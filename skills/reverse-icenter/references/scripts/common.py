import json
import os
import logging as log
import re
import time
from pathlib import Path
from types import SimpleNamespace

import requests
from bs4 import BeautifulSoup

log.basicConfig(
    level=log.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log.getLogger("httpx").setLevel(log.WARNING)

_config_data = {
    "prod": {
        "i_host": "https://i.zte.com.cn",
        "i_api_host": "https://icenterapi.zte.com.cn"
    }
}
config = SimpleNamespace(**_config_data.get("prod"))

CACHE_PATH = ".cache/icenter"
ARCHITECTURE_PATH = "architecture.json"
PAGE_IDS_FILE = f"{CACHE_PATH}/page_ids.json"
PAGE_FILE_PATH = f"{CACHE_PATH}/page"
ARCHITECTURE_DOC_LINKS_FILE = f"{CACHE_PATH}/architecture_doc_links"
EXTRACT_RESULTS_DIR = f"{CACHE_PATH}/extract_results"


def script_pre_check():
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True, help="仓库根目录")
    args = parser.parse_args()

    repo_root = os.path.abspath(args.repo_root)
    if not os.path.isdir(repo_root):
        log.error(f"错误：仓库根目录不存在: {repo_root}")
        sys.exit(1)
    os.chdir(repo_root)


def write_obj(output_file: str, data):
    write_file(output_file, json.dumps(data, ensure_ascii=False))


def write_file(file_path: str, content: str):
    # log.info(f"write file: {file_path}")
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except Exception as e:
        raise Exception(f"写入文件失败: {e}")


def read_json(file_path: str):
    return json.loads(read_file(file_path))


def read_file(file_path: str):
    return Path(file_path).read_text(encoding="utf-8")


def flat_page_tree(page_tree: list):
    result = []

    def preorder_traverse(node, parent_path):
        if not node:
            return
        name = node["name"]
        name = f"{parent_path}-{name}" if parent_path else name
        result.append({
            "id": node["id"],
            "name": name
        })

        for child in node.get("children", []):
            preorder_traverse(child, name)

    for tree in page_tree:
        preorder_traverse(tree, "")
    return result


def flat_concept_tree(concept_tree: list):
    result = []

    def preorder_traverse(node, parent_path):
        if not node:
            return
        parent_path.append(node["name"].replace("-", "_").replace("/", "_"))
        result.append({
            "name": parent_path,
            "source_documents": []
        })

        for child in node.get("children", []):
            preorder_traverse(child, parent_path.copy())

    for tree in concept_tree:
        preorder_traverse(tree, [])
    return result


def group_batch(data: list, batch_size=100, item_transfer=None):
    return [[item_transfer(i) if item_transfer else i for i in data[i:i + batch_size]]
            for i in range(0, len(data), batch_size)]


def concurrent_execute(func, arg_list: list, max_workers=5):
    import concurrent.futures
    from threading import Lock
    result_lock = Lock()
    result = []
    execute_idx = 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, arg): arg for arg in arg_list}

        for future in concurrent.futures.as_completed(futures):
            try:
                # log.info(f"execute progress: {execute_idx}/{len(arg_list)}")
                batch_result = future.result()
                execute_idx += 1
                with result_lock:
                    result.append(batch_result)
            except Exception as e:
                log.error(f"批次处理失败: {e}")
    return result


def get_md_title_tree_or_prefix_content(md_text: str):
    if len(md_text) < 100:
        return ""
    pattern = r"^(#{1,2})\s+(.+)$"
    matches = re.findall(pattern, md_text, re.MULTILINE)
    if matches:
        title_tree = []
        level_stack = []

        for marker, title_content in matches:
            level = len(marker)
            clean_title = title_content.strip().replace('*', '')

            current_node = {
                "title": clean_title
            }

            if level == 1:
                title_tree.append(current_node)
                level_stack = [current_node]
            elif level == 2:
                if len(level_stack) >= 1:
                    if len(level_stack) > 1:
                        level_stack.pop()
                    parent_node = level_stack[0]
                    if not parent_node.get("children"):
                        parent_node["children"] = []
                    parent_node["children"].append(current_node)
                    level_stack.append(current_node)
            elif level == 3:
                if len(level_stack) >= 2:
                    if len(level_stack) > 2:
                        level_stack.pop()
                    parent_node = level_stack[1]
                    if not parent_node.get("children"):
                        parent_node["children"] = []
                    parent_node["children"].append(current_node)
                    level_stack.append(current_node)
        if len(title_tree) >= 1 or title_tree[0].get("children"):
            return title_tree
    return md_text[:200]

def parse_icenter_url(url: str):
    pattern1 = r'https://i\.zte\.com\.cn/(?:[^/]+/)*ispace/#/(space|shared)/([^/]+)/wiki/page/([^/]+)/view'
    match1 = re.search(pattern1, url)

    if match1:
        space_type = match1.group(1)
        space_id = match1.group(2)
        page_id = match1.group(3)
        return space_id, page_id

    # https://i.zte.com.cn/#/space|shared/{space_id}/wiki/page/{page_id}/view
    pattern2 = r'https://i\.zte\.com\.cn/#/(space|shared)/([^/]+)/wiki/page/([^/]+)/view'
    match2 = re.search(pattern2, url)

    if match2:
        space_type = match2.group(1)
        space_id = match2.group(2)
        page_id = match2.group(3)
        return space_id, page_id

    # https://i.zte.com.cn/#/wiki/{space_id}/wiki/page/{page_id}/view
    pattern3 = r'https://i\.zte\.com\.cn/#/wiki/([^/]+)/wiki/page/([^/]+)/view'
    match3 = re.search(pattern3, url)

    if match3:
        space_id = match3.group(1)
        page_id = match3.group(2)
        return space_id, page_id

    log.error(f"无法解析URL格式: {url}")
    return None


class ICenterClient:
    def __init__(self):
        emp_no, auth_value = self._get_user_auth_info()

        self.user_header = {
            "X-Emp-No": emp_no,
            "X-auth-value": auth_value,
            "Content-Type": "application/json"
        }

    @staticmethod
    def _get_user_auth_info():
        ports = [19996, 5865, 29273]
        for port in ports:
            header = {
                "Referer": "https://uac.zte.com.cn/",
                "Host": f"127.0.0.1:{port}"
            }
            url = f"https://127.0.0.1:{port}/requestToken?callback=sme"
            try:
                response = requests.get(url, headers=header, timeout=2, verify=False)

                if response.status_code == 200:
                    body_txt = response.text.strip()

                    body_txt_fmt = body_txt[4:-1]

                    body_data = json.loads(body_txt_fmt)
                    emp_no = body_data.get("ZTEDPGSSOUser", "")
                    token = body_data.get("APPACCESSTOKEN", "")

                    return emp_no, token
            except Exception as e:
                log.warning(f"UDS接口端口 {port} 异常: {e}")
                continue

        error_msg = f"所有UDS接口端口都不可用: {ports}"
        log.error(error_msg)
        raise ValueError(error_msg)

    def call_dt_api(self, method, url: str, data, headers, timeout, retry_time: int = 3, sleep_time: int = 4):
        try:
            # log.info(f"{method} {url}\nbody: {json.dumps(data, ensure_ascii=False)}")
            response = requests.request(method, url, headers=headers, json=data, timeout=timeout)
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    log.exception(f"响应不是有效的JSON格式: {response.text}")
            else:
                log.exception(f"API调用失败，状态码: {response.status_code}, {response.text}")
            return {}
        except Exception as e:
            log.error(f"未知错误: {e}")
            while retry_time > 0:
                time.sleep(sleep_time)
                return self.call_dt_api(method, url, data, headers, timeout, retry_time=retry_time - 1,
                                        sleep_time=sleep_time * 2)
            return {}

    def get_dt_api(self, url: str, headers, data=None, timeout=2):
        return self.call_dt_api("GET", url, data, headers, timeout=timeout)

    @staticmethod
    def _get_page_file_path(page_param):
        return f".cache/icenter/page/{page_param[0]}-{page_param[1]}.md"

    def _get_page_detail(self, page_param):
        url = f"{config.i_host}/zte-rd-icenter-contents/content/{page_param[1]}?spaceId={page_param[0]}"
        bo = self.get_dt_api(url, self.user_header).get("bo", {})
        html_content = bo.get("contentBody", "")
        content = ""
        if html_content:
            content = self._html_to_markdown(html_content)
        return bo.get("title", ""), content

    def save_page_detail(self, page_param):
        file_name = self._get_page_file_path(page_param)
        if not os.path.exists(file_name):
            content = self._get_page_detail(page_param)
            content = f"# {content[0]}\n\n{content[1]}"
            write_file(file_name, content)

    @staticmethod
    def _html_to_markdown(html_content: str) -> str:
        from markdownify import markdownify as md_to_markdown
        try:
            return md_to_markdown(
                html_content or "",
                heading_style="ATX",
                strip=["script", "style"],
                escape_asterisks=False,
            ).strip()
        except Exception as e:
            log.error(f"transfer html 2 md failed, {e}")

        soup = BeautifulSoup(html_content or "", "html.parser")
        text_parts: list = []
        for block in soup.stripped_strings:
            text_parts.append(block)
        return "\n\n".join(text_parts)

    def get_all_children_pages(self, page_info_list: list):
        result = []
        for space_id, page_id in page_info_list:
            page = 1
            response = {}
            while page == 1 or response.get("bo", {}).get("hasNextPage", False):
                url = f"{config.i_api_host}/zte-rd-icenter-contents/content/nodes?contentId={page_id}&page={page}&size=1000&spaceId={space_id}&tags=0"
                page += 1
                response = self.get_dt_api(url, self.user_header, timeout=10)
                if response.get("code", {}).get("code") != "0000":
                    raise Exception(f"get children pages error: {response}")
                page_list = response.get("bo", {}).get("list", [])
                result.extend(
                    [{"id": page["id"], "name": page["title"], "parent_id": page["parentId"], "space_id": space_id}
                     for page in page_list])
        return result

    @staticmethod
    def transfer_page2id(page_info: list):
        id_map = {}
        id_map1 = {}
        data_list = []
        id_name_list = []
        for i, item in enumerate(page_info):
            id_map[i] = (item["space_id"], item["id"])
            id_map1[item["space_id"] + item["id"]] = i
            data_list.append({"id": i, "name": item["name"], "parent_id": item["space_id"] + item["parent_id"]})
            id_name_list.append({"id": i, "name": item["name"]})
        for item in data_list:
            item["parent_id"] = id_map1.get(item["parent_id"], None)
        return id_map, data_list, id_name_list

    @staticmethod
    def get_category_tree(category: list):
        node_map = {item["id"]: {"id": item["id"], "name": item["name"]} for item in category}
        origin_map = {item["id"]: item for item in category}
        tree = []
        for item in node_map.values():
            parent_node = node_map.get(origin_map[item["id"]]["parent_id"])
            if parent_node:
                if not parent_node.get("children", []):
                    parent_node["children"] = []
                parent_node["children"].append(item)
            else:
                tree.append(item)
        return tree
