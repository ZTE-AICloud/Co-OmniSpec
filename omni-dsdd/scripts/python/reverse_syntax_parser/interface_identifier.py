#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
接口识别模块 - 从调用链分析中识别接口函数
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class InterfaceIdentifier:
    def __init__(self, config, data_loader, llm_caller=None):
        self.config = config
        self.llm_caller = llm_caller  # None 表示不调用 LLM，全程使用启发式识别
        self.data_loader = data_loader
        self.max_concurrent = getattr(config, "max_concurrent", 20)
        self.call_tree_list = data_loader.load_call_tree()
        self.all_methods = data_loader.load_all_methods()
        self.all_functions = data_loader.load_all_functions()
        self.root_functions = []
        self.interface_functions = []
        self.output_dir = config.get_output_path("interface_identification")

    def extract_root_functions(self) -> List[Dict[str, Any]]:
        root_functions = []
        for call_tree in self.call_tree_list:
            root_name = call_tree.get("name", "")
            root_type = call_tree.get("type", "")
            if "###" in root_name:
                parts = root_name.split("###")
                func_name = parts[0]
                func_uuid = parts[1] if len(parts) > 1 else ""
            else:
                func_name = root_name
                func_uuid = ""
            root_functions.append({
                "name": func_name,
                "uuid": func_uuid,
                "full_identifier": root_name,
                "type": root_type,
                "call_tree": call_tree,
            })
        self.root_functions = root_functions
        return root_functions

    def get_function_content(self, func_uuid: str, func_name: str = None) -> Optional[Dict[str, Any]]:
        if func_uuid in self.all_functions:
            return self.all_functions[func_uuid]
        if func_uuid in self.all_methods:
            return self.all_methods[func_uuid]
        if func_name:
            full_key = f"{func_name}###{func_uuid}"
            if full_key in self.all_functions:
                return self.all_functions[full_key]
            if full_key in self.all_methods:
                return self.all_methods[full_key]
        for key, value in self.all_methods.items():
            if func_uuid in key or value.get("uuid") == func_uuid:
                return value
        for key, value in self.all_functions.items():
            if func_uuid in key or value.get("uuid") == func_uuid:
                return value
        return None

    @staticmethod
    def _is_test_file(filename: str) -> bool:
        """判断是否为测试文件（test 目录下的文件不应被识别为接口）"""
        if not filename:
            return False
        normalized = filename.replace("\\", "/")
        parts = normalized.split("/")
        return any(p in ("test", "tests") for p in parts) or any(
            p.startswith("test_") for p in parts
        )

    def _heuristic_identify_interface(self, func_content: Dict[str, Any]) -> Dict[str, Any]:
        """LLM 不可用时的启发式接口识别（覆盖提示词模板中定义的全部接口类型）"""
        name = func_content.get("name", "")
        content = func_content.get("content", "") or ""
        filename = func_content.get("filename", "") or ""
        decorators = func_content.get("decorators", [])
        dec_str = " ".join(str(d) for d in decorators).lower()
        content_lower = content.lower()
        content_head = content[:600]
        content_head_lower = content_head.lower()

        def _result(is_iface, itype, confidence, basis, desc=None):
            return {
                "is_interface": is_iface,
                "interface_type": itype,
                "confidence": confidence,
                "judgment_basis": basis,
                "endpoint": "",
                "http_method": "",
                "description": desc or name or ("接口" if is_iface else ""),
            }

        # --- 0. 测试文件过滤 & 特殊方法过滤 ---
        if self._is_test_file(filename):
            return _result(False, "未知", 0.0, "启发式：测试文件，跳过")
        if name.startswith("__") and name.endswith("__"):
            return _result(False, "未知", 0.0, "启发式：Python 特殊方法，跳过")

        # --- 1. RESTful 接口 ---
        route_decorator_patterns = [
            "app.route", "router.get", "router.post", "router.put", "router.delete",
            "router.patch", "api.route", "blueprint.route", ".route(",
            "api_view", "action(detail=", "action(methods=",
        ]
        for p in route_decorator_patterns:
            if p in dec_str:
                return _result(True, "RESTful API", 0.7, f"启发式：装饰器命中 {p}")

        django_view_patterns = [
            "httpresponse", "jsonresponse", "render(request",
            "request.method", "request.get", "request.post",
        ]
        if any(p in content_head_lower for p in django_view_patterns):
            if name in ("get", "post", "put", "patch", "delete", "list", "create", "update", "destroy", "retrieve"):
                return _result(True, "RESTful API", 0.65, "启发式：Django/DRF 视图方法")

        # --- 2. OpenStack 插件接口（提前检测，优先于消息接口）---
        openstack_patterns = [
            "stevedore", "extensionmanager", "drivermanager",
            "namedextensionmanager", "entry_points",
            "oslo.messaging", "oslo_messaging", "oslo.service",
        ]
        if any(p in content_head_lower for p in openstack_patterns):
            return _result(True, "OpenStack插件接口", 0.6, "启发式：含 stevedore/oslo 特征")

        openstack_method_names = [
            "create", "delete", "update", "attach", "detach", "bind_port",
            "create_network", "delete_network", "create_port", "delete_port",
            "create_subnet", "delete_subnet",
        ]
        if name in openstack_method_names:
            if any(ns in content_lower for ns in ("neutron", "cinder", "nova", "keystone", "glance")):
                return _result(True, "OpenStack插件接口", 0.55, "启发式：OpenStack 服务方法")

        openstack_plugin_content_patterns = [
            "restmessage", "rest_message", "servermanager",
        ]
        openstack_plugin_path_patterns = [
            "_plugin.py", "_driver.py", "_handler.py",
        ]
        openstack_path_prefixes = ["code", "networking_", "neutron_"]
        filename_lower = filename.lower()
        is_plugin_file = any(p in filename_lower for p in openstack_plugin_path_patterns)
        is_openstack_ns = any(p in filename_lower for p in openstack_path_prefixes)
        has_openstack_content = any(p in content_head_lower for p in openstack_plugin_content_patterns)

        openstack_crud_prefixes = (
            "create_", "delete_", "update_", "add_", "remove_",
            "bind_", "unbind_", "attach_", "detach_", "bulk_",
        )
        is_crud_method = any(name.startswith(pfx) for pfx in openstack_crud_prefixes)
        has_context_param = "self, context" in content_head[:200]

        if is_openstack_ns and is_plugin_file and is_crud_method and has_context_param:
            return _result(True, "OpenStack插件接口", 0.65, "启发式：OpenStack 插件文件 + CRUD + context")

        if is_openstack_ns and has_openstack_content and is_crud_method:
            return _result(True, "OpenStack插件接口", 0.6, "启发式：OpenStack 命名空间 + REST通信 + CRUD")

        if is_crud_method and has_context_param and has_openstack_content:
            return _result(True, "OpenStack插件接口", 0.55, "启发式：CRUD 方法 + context + REST通信特征")

        # --- 3. 系统接口（CLI）---
        cli_names = ("main", "run", "execute", "cli", "entry_point", "app")
        cli_markers = ("argparse", "click", "__name__", "sys.argv", "typer", "fire.Fire")
        if name in cli_names:
            if any(m in content_head for m in cli_markers):
                return _result(True, "命令行接口", 0.6, "启发式：入口函数且含参数解析", name or "入口")

        # --- 4. RPC 接口 ---
        rpc_patterns = [
            "grpc", "pb2_grpc", "servicer", "add_.*_to_server",
            "thrift", "xmlrpc", "jsonrpc", "xml_rpc", "json_rpc",
        ]
        if any(re.search(p, content_head_lower) for p in rpc_patterns):
            return _result(True, "RPC接口", 0.65, "启发式：含 gRPC/Thrift/RPC 特征")
        rpc_dec_patterns = ["grpc", "rpc", "xmlrpc", "jsonrpc"]
        if any(p in dec_str for p in rpc_dec_patterns):
            return _result(True, "RPC接口", 0.7, "启发式：装饰器含 RPC 特征")

        # --- 5. 消息接口（精化：排除 REST 通信场景中的 send_msg）---
        rest_comm_indicators = ["restmessage", "rest_message", "httplib", "requests.", "urllib"]
        is_rest_comm = any(p in content_head_lower for p in rest_comm_indicators)

        msg_patterns = [
            "__async", "__sync", "decl_trans", "wait_on",
            "asyncaction", "async_action",
        ]
        msg_send_patterns = ["sendmsg", "send_msg", "send_message"]
        if any(p in content_head_lower for p in msg_patterns):
            return _result(True, "消息接口", 0.6, "启发式：含事务/消息发送特征")
        if not is_rest_comm and any(p in content_head_lower for p in msg_send_patterns):
            return _result(True, "消息接口", 0.6, "启发式：含消息发送特征（非 REST 通信）")

        msg_type_patterns = ["pdu", "ev_"]
        if any(p in content_lower for p in msg_type_patterns):
            if "message" in content_lower or "event" in content_lower:
                return _result(True, "消息接口", 0.55, "启发式：含消息/事件类型特征")

        # --- 6. 消息队列接口 ---
        mq_patterns = [
            "kafka", "rabbitmq", "pika", "kombu", "celery",
            "redis.pubsub", "pubsub", "consumer", "producer",
            "pulsar", "amazonaws.sqs", "sqs_client",
        ]
        mq_dec_patterns = ["task", "shared_task", "celery.task", "consumer"]
        if any(p in content_head_lower for p in mq_patterns):
            return _result(True, "消息队列接口", 0.6, "启发式：含消息队列中间件特征")
        if any(p in dec_str for p in mq_dec_patterns):
            return _result(True, "消息队列接口", 0.65, "启发式：装饰器含消息队列/Task 特征")

        # --- 7. WebSocket 接口 ---
        ws_patterns = ["websocket", "ws_connect", "on_message", "on_connect", "on_close", "socketio"]
        ws_dec_patterns = ["websocket", "socketio", "sio.event", "sio.on"]
        if any(p in content_head_lower for p in ws_patterns) or any(p in dec_str for p in ws_dec_patterns):
            return _result(True, "WebSocket接口", 0.6, "启发式：含 WebSocket 特征")

        # --- 8. 定时任务接口 ---
        schedule_dec_patterns = ["schedule", "crontab", "periodic_task", "cron"]
        if any(p in dec_str for p in schedule_dec_patterns):
            return _result(True, "定时任务接口", 0.6, "启发式：装饰器含定时任务特征")

        # 无强信号时：不视为接口
        return _result(False, "未知", 0.0, "启发式：无接口特征，建议配置 LLM 以提升识别")

    def identify_interface_with_llm(self, root_func: Dict[str, Any]) -> Dict[str, Any]:
        func_content = self.get_function_content(root_func["uuid"], root_func["name"])
        if not func_content:
            return {
                "is_interface": False,
                "interface_type": "未知",
                "confidence": 0.0,
                "judgment_basis": "无法获取函数内容",
                "endpoint": "",
                "http_method": "",
                "description": "",
            }
        if not self.llm_caller:
            return self._heuristic_identify_interface(func_content)
        template_vars = {
            "method_name": func_content.get("name", "Unknown"),
            "filename": func_content.get("filename", "Unknown"),
            "function_type": func_content.get("type", "Unknown"),
            "method_content": func_content.get("content", ""),
            "params_json": json.dumps(func_content.get("params", []), ensure_ascii=False, indent=2),
            "decorators_json": json.dumps(func_content.get("decorators", []), ensure_ascii=False, indent=2),
        }
        try:
            response_text = self.llm_caller(template_vars)
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                if result.get("is_interface") or result.get("interface_type") not in ("识别失败", "未知"):
                    return result
            raise ValueError("无法从响应中提取有效JSON")
        except Exception as e:
            logger.warning("LLM 不可用，使用启发式识别: %s", e)
            return self._heuristic_identify_interface(func_content)

    def analyze_all_root_functions(self) -> List[Dict[str, Any]]:
        import threading
        results = []
        total = len(self.root_functions)
        completed_count = 0
        interface_count = 0
        count_lock = threading.Lock()

        def analyze_one(i: int, root_func: Dict[str, Any]) -> Dict[str, Any]:
            nonlocal completed_count, interface_count
            identification_result = self.identify_interface_with_llm(root_func)
            func_content = self.get_function_content(root_func["uuid"], root_func["name"])
            result = {
                "root_function": root_func["name"],
                "full_identifier": root_func["full_identifier"],
                "uuid": root_func["uuid"],
                "is_interface": identification_result.get("is_interface", False),
                "interface_type": identification_result.get("interface_type", "未知"),
                "confidence": identification_result.get("confidence", 0.0),
                "description": identification_result.get("description", ""),
                "judgment_basis": identification_result.get("judgment_basis", ""),
                "endpoint": identification_result.get("endpoint", ""),
                "http_method": identification_result.get("http_method", ""),
                "belonging_file": func_content.get("filename", "未知") if func_content else "未知",
                "call_tree": root_func["call_tree"],
                "index": i,
            }
            if result["is_interface"]:
                with count_lock:
                    self.interface_functions.append(result)
                    interface_count += 1
            with count_lock:
                completed_count += 1
                if completed_count % 50 == 0 or completed_count == total:
                    logger.info(
                        "进度: %d/%d (%.1f%%), 已识别接口: %d",
                        completed_count, total,
                        completed_count / total * 100,
                        interface_count,
                    )
            return result

        logger.info("开始分析 %d 个根函数（并发数: %d）...", total, self.max_concurrent)
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            all_results = list(executor.map(
                lambda x: analyze_one(x[0], x[1]),
                enumerate(self.root_functions),
            ))
        results = sorted(all_results, key=lambda x: x.get("index", 0))
        for r in results:
            r.pop("index", None)
        return results

    def generate_interface_functions_checklist(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        checklist_path = self.output_dir / "interface_functions_checklist.json"
        checklist = []
        for i, interface in enumerate(self.interface_functions):
            safe_desc = interface.get("description", "")
            for c in ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]:
                safe_desc = safe_desc.replace(c, "_")
            api_id = f"API-{i+1:03d}"
            checklist.append({
                "interface_function": interface["root_function"],
                "full_identifier": interface["full_identifier"],
                "api_id": api_id,
                "uuid": interface["uuid"],
                "interface_type": interface["interface_type"],
                "endpoint": interface["endpoint"],
                "http_method": interface["http_method"],
                "belonging_file": interface["belonging_file"],
                "interface_file": f"API_{i+1:03d}_{safe_desc}.json",
            })
        with open(checklist_path, "w", encoding="utf-8") as f:
            json.dump(checklist, f, ensure_ascii=False, indent=2)
        logger.info("接口函数清单已保存: %s", checklist_path)
        return checklist_path

    def run(self) -> Dict[str, Any]:
        try:
            self.extract_root_functions()
            self.analyze_all_root_functions()
            checklist_path = self.generate_interface_functions_checklist()
            return {
                "status": "success",
                "message": "接口识别完成",
                "statistics": {
                    "total_root_functions": len(self.root_functions),
                    "total_interfaces": len(self.interface_functions),
                },
                "outputs": {"interface_checklist": checklist_path},
            }
        except Exception as e:
            logger.error("接口识别失败: %s", e, exc_info=True)
            return {"status": "error", "message": str(e)}
