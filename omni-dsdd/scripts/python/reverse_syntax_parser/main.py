#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reverse_syntax_parser 入口
--step identify: 执行 prepare + identify，输出 interface_functions_checklist.json
"""
from __future__ import print_function

import sys
if sys.version_info < (3, 6):
    sys.stderr.write("此脚本需要 Python 3.6+，请使用: python3 main.py ...\n")
    sys.exit(1)

import argparse
import os
from pathlib import Path

# 确保可导入本包（reverse_syntax_parser 位于 .omni-infra/scripts/python/ 或源码树 scripts/python/）
_SCRIPT_DIR = Path(__file__).resolve().parent
_PYTHON_DIR = _SCRIPT_DIR.parent
if str(_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(_PYTHON_DIR))

from utils import (
    get_logger,
    load_config_from_env,
    call_llm_with_prompts,
)
from data_loader import DataLoader, SimplePathConfig
from interface_identifier import InterfaceIdentifier
from get_code_type import CodeLanguageDetector
from syntax_parser import (
    python_code_syntax_parsing,
    cpp_code_syntax_parsing,
    java_code_syntax_parsing,
    c_code_syntax_parsing
)
from semantics_parser import generate_call_tree


def _load_prompt_template(prompts_dir):
    """加载 interface_classification 模板，返回 (system_prompt, user_template)"""
    md_path = prompts_dir / "interface_classification.md"
    if not md_path.exists():
        raise OSError("Prompt 模板不存在: {}".format(md_path))
    content = md_path.read_text(encoding="utf-8")
    lines = content.split("\n")
    system_lines = []
    user_lines = []
    in_system = False
    in_user = False
    for line in lines:
        if "## 系统提示词" in line:
            in_system = True
            in_user = False
            continue
        if "## 用户提示词模板" in line or "## 函数信息" in line:
            in_system = False
            in_user = True
            if "## 函数信息" in line:
                user_lines.append(line)
            continue
        if in_system:
            system_lines.append(line)
        elif in_user:
            user_lines.append(line)
    system_prompt = "\n".join(system_lines).strip()
    user_template = "\n".join(user_lines).strip()
    return system_prompt, user_template


def _create_llm_caller(prompts_dir, config, logger):
    """创建可调用的 LLM caller，接收 template_vars，返回 response 字符串"""
    system_prompt, user_template = _load_prompt_template(prompts_dir)

    def caller(template_vars):
        try:
            user_prompt = user_template.format(**template_vars)
        except KeyError as e:
            raise ValueError("模板变量缺失: {}".format(e))
        return call_llm_with_prompts(
            system_prompt, user_prompt, config=config, logger=logger
        )

    return caller


def run_prepare(codebase, input_base_dir, logger):
    """执行 prepare：语言检测 -> 语法解析 -> 语义解析"""
    detector = CodeLanguageDetector()
    language = detector.detect_language(str(codebase))
    logger.info(f"检测到代码库语言: {language}")

    # 检查各语言解析器的可用性
    # 使用绝对导入
    import sys
    import os
    sys.path.insert(0, str(Path(__file__).parent))
    from syntax_parser import (
        python_code_syntax_parsing,
        cpp_code_syntax_parsing,
        java_code_syntax_parsing,
        c_code_syntax_parsing,
        CPP_PARSER_AVAILABLE,
        C_PARSER_AVAILABLE,
        JAVA_PARSER_AVAILABLE
    )

    # 语言到解析器的映射
    language_parsers = {
        "python": python_code_syntax_parsing,
        "cpp": cpp_code_syntax_parsing if CPP_PARSER_AVAILABLE else None,
        "c": c_code_syntax_parsing if C_PARSER_AVAILABLE else None,
        "java": java_code_syntax_parsing if JAVA_PARSER_AVAILABLE else None,
    }

    # 检查语言支持
    parser_func = language_parsers.get(language)
    if not parser_func:
        # 如果不支持该语言，尝试降级到Python
        logger.warning(f"当前系统尚不支持 {language} 语言的完整解析，转为使用Python兼容模式")
        py_files = list(Path(codebase).rglob("*.py"))
        if not py_files:
            # 提供更详细的错误信息
            supported_langs = [lang for lang, parser in language_parsers.items() if parser is not None]
            raise ValueError(
                f"不支持的语言: {language}。\n"
                f"当前支持的语言: {', '.join(supported_langs)}。\n"
                f"如需支持其他语言，请安装缺少的依赖（如 tree-sitter）。\n"
                f"详情请参考 MULTI_LANGUAGE_SUPPORT.md"
            )
        language = "python"
        parser_func = python_code_syntax_parsing
        logger.info(f"找到 {len(py_files)} 个Python文件，将进行Python语言解析")

    syntax_out = input_base_dir / "internal" / "syntax_parser"
    semantics_out = input_base_dir / "internal" / "semantics_parser"
    syntax_out.mkdir(parents=True, exist_ok=True)
    semantics_out.mkdir(parents=True, exist_ok=True)

    # 保存检测到的语言类型，供后续步骤使用
    language_info = {"language": language, "related_json_files": []}
    # 直接使用简单的JSON保存
    with open(str(syntax_out / "code_type.json"), "w", encoding="utf-8") as f:
        import json
        json.dump(language_info, f, ensure_ascii=False, indent=2)

    # 执行对应语言的语法解析
    logger.info(f"开始执行 {language} 语法解析...")
    try:
        parser_func(str(codebase), str(syntax_out))
        logger.info(f"{language} 语法解析完成")
    except Exception as e:
        logger.error(f"{language} 语法解析失败: {str(e)}")
        raise

    # 调用语义解析器（调用链生成），目前对所有语言都使用相同的逻辑
    logger.info("开始生成调用链...")
    generate_call_tree(str(syntax_out), str(semantics_out), logger)
    logger.info("调用链生成完成")


def run_identify(input_base_dir, logger, no_llm=False):
    """执行 identify，返回 interface_functions_checklist.json 路径"""
    config = SimplePathConfig(str(input_base_dir), str(input_base_dir))
    config.max_concurrent = int(os.environ.get("OPENAI_MAX_CONCURRENT", "20"))  # type: ignore
    data_loader = DataLoader(config)
    prompts_dir = _SCRIPT_DIR / "prompts"
    llm_config = load_config_from_env(str(input_base_dir))
    if no_llm:
        logger.info("已通过 --no-llm 参数禁用 LLM，全程使用启发式识别。")
        llm_caller = None
    elif not (llm_config.get("api_key") or "").strip():
        logger.warning(
            "未配置 LLM API Key，全程使用启发式识别。"
            "如需 LLM 识别：请设置环境变量 OPENAI_API_KEY，或在本模块同目录 llm-config.yaml 中配置 api_key（需安装 PyYAML）。"
        )
        llm_caller = None
    else:
        llm_caller = _create_llm_caller(prompts_dir, llm_config, logger)
    identifier = InterfaceIdentifier(config, data_loader, llm_caller)
    result = identifier.run()
    if result["status"] != "success":
        raise RuntimeError(result.get("message", "接口识别失败"))
    return result["outputs"]["interface_checklist"]


def main():
    logger = get_logger("reverse_syntax_parser")
    parser = argparse.ArgumentParser(description="接口获取 - prepare + identify")
    parser.add_argument("--step", choices=["identify", "prepare"], default="identify")
    parser.add_argument("--input-base-dir", required=True, help="input_base_dir（含 internal/syntax_parser, internal/semantics_parser）")
    parser.add_argument("--codebase", help="代码库路径（prepare 时必填）")
    parser.add_argument("--no-llm", action="store_true", default=False, help="禁用 LLM，仅使用启发式识别")
    args = parser.parse_args()

    input_base_dir = Path(args.input_base_dir).resolve()
    if not input_base_dir.exists():
        input_base_dir.mkdir(parents=True, exist_ok=True)

    if args.step == "prepare":
        if not args.codebase:
            logger.error("--step prepare 需要 --codebase")
            sys.exit(1)
        run_prepare(Path(args.codebase), input_base_dir, logger)
        logger.info("prepare 完成: %s", input_base_dir)
        return

    if args.step == "identify":
        # identify 前若依赖不存在，先执行 prepare
        semantics_dir = input_base_dir / "internal" / "semantics_parser"
        call_tree = semantics_dir / "call_tree_list.json"
        if not call_tree.exists() and args.codebase:
            logger.info("前置依赖不存在，先执行 prepare")
            run_prepare(Path(args.codebase), input_base_dir, logger)
        elif not call_tree.exists():
            logger.error("缺少 call_tree_list.json，请先运行 prepare 或提供 --codebase")
            sys.exit(1)
        out_path = run_identify(input_base_dir, logger, no_llm=getattr(args, "no_llm", False))
        logger.info("identify 完成，输出: %s", out_path)
        print(str(out_path))


if __name__ == "__main__":
    main()
