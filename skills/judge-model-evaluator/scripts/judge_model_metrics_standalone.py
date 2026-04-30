"""独立运行脚本：计算基于第三方裁判模型的分级评估指标（ICE Score + Code Judge）"""

import argparse
import re
import json
import sys
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
from jinja2 import Template
from loguru import logger as log


# ==================== API 配置（从配置文件加载） ====================

API_URL = ""
API_KEY = ""
MODEL_NAME = ""
API_TIMEOUT = 60
API_MAX_TOKENS = 16384
API_TEMPERATURE = 0.1

DEFAULT_PROBLEM = "代码生成任务"


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件并设置全局 API 参数"""
    global API_URL, API_KEY, MODEL_NAME, API_TIMEOUT, API_MAX_TOKENS, API_TEMPERATURE

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    api_cfg = config.get("api", {})
    API_URL = api_cfg.get("url", API_URL)
    API_KEY = api_cfg.get("key", API_KEY)
    MODEL_NAME = api_cfg.get("model_name", MODEL_NAME)
    API_TIMEOUT = api_cfg.get("timeout", API_TIMEOUT)
    API_MAX_TOKENS = api_cfg.get("max_tokens", API_MAX_TOKENS)
    API_TEMPERATURE = api_cfg.get("temperature", API_TEMPERATURE)

    return config

# 模板根路径
TEMPLATE_BASE_PATH = Path(__file__).parent / "prompts"

ICE_TEMPLATE_MAP = {
    ("functional_correctness", True): "ice_score_functional_correctness_with_answer.jinja2",
    ("functional_correctness", False): "ice_score_functional_correctness_no_answer.jinja2",
    ("usefulness", True): "ice_score_usefulness_with_answer.jinja2",
    ("usefulness", False): "ice_score_usefulness_no_answer.jinja2",
}

CODE_JUDGE_TEMPLATE_MAP = {
    ("v1", True): "code_judge_with_answer_v1.jinja2",
    ("v1", False): "code_judge_no_answer_v1.jinja2",
    ("v2", True): "code_judge_with_answer_v2.jinja2",
    ("v2", False): "code_judge_no_answer_v2.jinja2",
}


# ==================== 通用工具函数 ====================

def call_model_api(prompt: str) -> Optional[str]:
    """调用模型 API"""
    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL_NAME,
        "max_tokens": API_MAX_TOKENS,
        "temperature": API_TEMPERATURE,
        "stream": False,
        "messages": [
            {"role": "system", "content": "You are an AI assistant."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=API_TIMEOUT)
        response.raise_for_status()
        response_data = response.json()

        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content'].strip()
        else:
            log.error(f"API返回格式异常: {response_data}")
            return None
    except requests.exceptions.RequestException as e:
        log.error(f"API调用出错: {e}")
        return None
    except Exception as e:
        log.error(f"处理API响应时出错: {e}")
        return None


def load_template(template_map: Dict, key: tuple) -> Optional[Template]:
    """加载 Jinja2 模板"""
    if key not in template_map:
        log.error(f"不支持的模板键: {key}")
        return None

    template_filename = template_map[key]
    template_path = TEMPLATE_BASE_PATH / template_filename

    if not template_path.is_file():
        log.error(f"模板文件不存在: {template_path}")
        return None

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return Template(f.read())
    except Exception as e:
        log.error(f"加载模板失败: {e}")
        return None


# ==================== ICE Score 相关 ====================

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """从模型返回的文本中提取 JSON 数据"""
    try:
        json_data = json.loads(text)
        if isinstance(json_data, dict):
            return json_data
    except json.JSONDecodeError:
        pass
    except Exception as e:
        log.debug(f"JSON解析时出错: {e}")

    try:
        json_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        json_blocks = re.findall(json_block_pattern, text, re.DOTALL | re.IGNORECASE)
        for block in json_blocks:
            try:
                json_data = json.loads(block.strip())
                if isinstance(json_data, dict):
                    return json_data
            except json.JSONDecodeError:
                continue
    except Exception as e:
        log.debug(f"提取JSON代码块时出错: {e}")

    return None


def extract_score(text: str) -> Optional[int]:
    """从模型返回的文本中提取分数（0-4）"""
    json_data = extract_json_from_text(text)
    if json_data and "score" in json_data:
        score = json_data["score"]
        if isinstance(score, (int, float)):
            score_int = int(score)
            if 0 <= score_int <= 4:
                return score_int

    patterns = [
        r'(?:Functional Correctness|Usefulness)\s*\(?scores?\s*ONLY\)?\s*[:：]?\s*(\d)',
        r'(?:score|分数|评分)\s*[:：]?\s*(\d)',
        r'"score"\s*[:：]\s*(\d)',
        r'\b(\d)\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if 0 <= score <= 4:
                return score

    numbers = re.findall(r'\b([0-4])\b', text)
    if numbers:
        return int(numbers[0])

    log.warning(f"无法从文本中提取分数: {text[:200]}")
    return None


def extract_justification(text: str) -> Optional[Dict[str, Any]]:
    """从模型返回的文本中提取 justification 字段"""
    json_data = extract_json_from_text(text)
    if json_data and "justification" in json_data:
        justification = json_data["justification"]
        if isinstance(justification, dict):
            return justification
    return None


def calculate_ice_score(
    problem: str,
    output: str,
    metric_type: Literal["functional_correctness", "usefulness"],
    reference: Optional[str] = None
) -> Dict[str, Any]:
    """计算 ICE 分数（Functional Correctness 或 Usefulness）"""
    result = {"score": None, "raw_response": None, "error": None}

    if metric_type not in ["functional_correctness", "usefulness"]:
        result["error"] = f"不支持的指标类型: {metric_type}"
        return result

    if not problem or not output:
        result["error"] = "problem 和 output 不能为空"
        return result

    has_reference = reference is not None and reference.strip() != ""
    template = load_template(ICE_TEMPLATE_MAP, (metric_type, has_reference))
    if not template:
        result["error"] = "无法加载模板"
        return result

    try:
        template_data = {"PROBLEM": problem, "OUTPUT": output}
        if has_reference:
            template_data["REFERENCE"] = reference
        prompt = template.render(**template_data)
    except Exception as e:
        result["error"] = f"渲染模板失败: {e}"
        return result

    raw_response = call_model_api(prompt)
    if not raw_response:
        result["error"] = "API调用失败或返回为空"
        return result

    result["raw_response"] = raw_response
    score = extract_score(raw_response)
    result["score"] = score

    justification = extract_justification(raw_response)
    if justification:
        result["justification"] = justification

    if score is None:
        result["error"] = "无法从模型响应中提取有效分数"

    return result


def calculate_both_scores(
    problem: str,
    output: str,
    reference: Optional[str] = None
) -> Dict[str, Any]:
    """同时计算 Functional Correctness 和 Usefulness 两个指标"""
    return {
        "functional_correctness": calculate_ice_score(problem, output, "functional_correctness", reference),
        "usefulness": calculate_ice_score(problem, output, "usefulness", reference)
    }


# ==================== Code Judge 相关 ====================

def extract_inconsistencies(text: str) -> Optional[List[Dict[str, str]]]:
    """从模型返回的文本中提取不一致性列表"""
    json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    json_array_match = re.search(r'(\[.*?\])', text, re.DOTALL)
    if json_array_match:
        try:
            return json.loads(json_array_match.group(1))
        except json.JSONDecodeError:
            pass

    try:
        cleaned_text = text.strip()
        if cleaned_text.startswith('```'):
            cleaned_text = re.sub(r'```(?:json)?\s*', '', cleaned_text)
            cleaned_text = re.sub(r'\s*```', '', cleaned_text)
        parsed = json.loads(cleaned_text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    log.warning(f"无法从文本中提取JSON格式的不一致性列表: {text[:200]}")
    return None


def count_inconsistencies_by_severity(inconsistencies: List[Dict[str, str]]) -> Dict[str, int]:
    """统计不一致性列表中各类别（按 severity）的数量"""
    counts = {"Small": 0, "Major": 0, "Fatal": 0}
    if not inconsistencies:
        return counts
    for item in inconsistencies:
        severity = item.get("severity", "")
        if severity in counts:
            counts[severity] += 1
    return counts


def calculate_code_judge_score(inconsistencies: Optional[List[Dict[str, str]]]) -> float:
    """根据不一致性列表计算 code judge 分数（0-100）"""
    if inconsistencies is None or len(inconsistencies) == 0:
        return 100.0

    if len(inconsistencies) == 1 and inconsistencies[0].get("inconsistency") == "None":
        return 100.0

    counts = count_inconsistencies_by_severity(inconsistencies)
    total_penalty = counts["Small"] * 5 + counts["Major"] * 50 + counts["Fatal"] * 100
    penalty = min(100, total_penalty)
    return max(0.0, 100.0 - penalty)


def calculate_code_judge(
    problem: str,
    code_snippet: str,
    version: Literal["v1", "v2"],
    reference: Optional[str] = None
) -> Dict[str, Any]:
    """计算代码判断指标"""
    result = {"inconsistencies": None, "raw_response": None, "error": None, "score": 100.0}

    if version not in ["v1", "v2"]:
        result["error"] = f"不支持的版本: {version}"
        return result

    if not problem or not code_snippet:
        result["error"] = "problem 和 code_snippet 不能为空"
        return result

    has_reference = reference is not None and reference.strip() != ""
    template = load_template(CODE_JUDGE_TEMPLATE_MAP, (version, has_reference))
    if not template:
        result["error"] = "无法加载模板"
        return result

    try:
        template_data = {"PROBLEM": problem, "CODE1": code_snippet}
        if has_reference:
            template_data["CODE2"] = reference
        prompt = template.render(**template_data)
    except Exception as e:
        result["error"] = f"渲染模板失败: {e}"
        return result

    raw_response = call_model_api(prompt)
    if not raw_response:
        result["error"] = "API调用失败或返回为空"
        return result

    result["raw_response"] = raw_response
    inconsistencies = extract_inconsistencies(raw_response)
    result["inconsistencies"] = inconsistencies

    if inconsistencies is None:
        result["error"] = "无法从模型响应中提取有效的不一致性列表"
    else:
        result["score"] = calculate_code_judge_score(inconsistencies)

    return result


# ==================== 问题描述提取 ====================

def parse_feature_info_item(feature: Any) -> Optional[Dict]:
    """解析单个 feature_info 项，支持字典和字符串格式"""
    if isinstance(feature, dict):
        return feature
    elif isinstance(feature, str):
        try:
            parsed = json.loads(feature)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return {"变更描述": feature}
    return None


def find_change_description_keys(parsed_item: Dict) -> List[str]:
    """查找同时包含'变更'和'描述'的键"""
    matched_keys = []
    for key in parsed_item.keys():
        if not isinstance(key, str):
            continue
        if "变更" in key and "描述" in key:
            matched_keys.append(key)
    return matched_keys


def get_change_description(parsed_item: Dict) -> str:
    """获取变更描述信息"""
    keys = find_change_description_keys(parsed_item)
    for key in keys:
        value = parsed_item.get(key, "")
        if value and isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def extract_problem_description(feature_infos: List) -> str:
    """从 feature_infos 提取问题描述"""
    if not feature_infos:
        return DEFAULT_PROBLEM

    descriptions = []
    if isinstance(feature_infos, list):
        for item in feature_infos:
            parsed_item = parse_feature_info_item(item)
            if not parsed_item:
                continue
            desc = get_change_description(parsed_item)
            if desc:
                descriptions.append(desc)

    if descriptions:
        return "; ".join(descriptions)

    return DEFAULT_PROBLEM

def extract_code_blocks_from_list(code_list: List) -> List[str]:
        """从代码列表中提取所有字符串代码块"""
        code_blocks = []
        if isinstance(code_list, list):
            for code_block in code_list:
                if isinstance(code_block, str):
                    code_blocks.append(code_block)
        return code_blocks
    
def extract_model_code_blocks(model_code_blocks: Dict) -> str:
    """从模型结果中提取所有代码块，合并为字符串"""
    if not isinstance(model_code_blocks, dict):
        return ""
    
    all_blocks = []
    for filepath, code_list in model_code_blocks.items():
        blocks = extract_code_blocks_from_list(code_list)
        all_blocks.extend(blocks)
    
    return "\n".join(all_blocks)


# ==================== 指标计算 ====================

def compute_ice_score(problem: str, code_blocks: str, reference: Optional[str]) -> Dict[str, Any]:
        """计算ICE Score指标"""
        try:
            log.info("开始计算ICE Score指标")
            ice_result = calculate_both_scores(
                problem=problem,
                output=code_blocks,
                reference=reference
            )
            # 将 functional_correctness 和 usefulness 的 score 转换为百分制
            fc_result = ice_result["functional_correctness"]
            usefulness_result = ice_result["usefulness"]
            fc_score = fc_result.get("score")
            usefulness_score = usefulness_result.get("score")

            result = {
                "functional_correctness": {
                    "score": fc_score / 4.0 if fc_score is not None else None,
                    "error": fc_result.get("error"),
                    "justification": fc_result.get("justification")  # 新增：传递justification字段
                },
                "usefulness": {
                    "score": usefulness_score / 4.0 if usefulness_score is not None else None,
                    "error": usefulness_result.get("error"),
                    "justification": usefulness_result.get("justification")  # 新增：传递justification字段
                }
            }
            log.info(f"ICE Score计算完成: functional_correctness={fc_score}, "
                     f"usefulness={usefulness_score}")
            return result
        except Exception as e:
            log.error(f"计算ICE Score时出错: {e}")
            return {
                "functional_correctness": {"score": None, "error": str(e), "justification": None},
                "usefulness": {"score": None, "error": str(e), "justification": None}
            }

def count_inconsistencies(judge_result: Dict):
    """计算不一致项的数量"""
    if judge_result.get('is_correct'):
        return 0
    inconsistencies = judge_result.get('inconsistencies')
    return len(inconsistencies) if inconsistencies is not None else None


def compute_code_judge(problem: str, code_blocks: str, reference: Optional[str]) -> Dict[str, Any]:
    """计算 Code Judge 指标"""
    try:
        log.info("开始计算Code Judge指标")
        code_judge_result = calculate_code_judge(problem, code_blocks, "v2", reference)
        code_judge_score = code_judge_result.get("score")

        result = {
            "score": code_judge_score / 100.0,
            "inconsistencies": code_judge_result.get("inconsistencies"),
            "inconsistencies_count": count_inconsistencies(code_judge_result),
            "error": code_judge_result.get("error")
        }
        log.info(f"Code Judge计算完成: score={code_judge_result.get('score')}")
        return result
    except Exception as e:
        log.error(f"计算Code Judge时出错: {e}")
        return {
            "score": None,
            "inconsistencies": None,
            "inconsistencies_count": None,
            "error": str(e)
        }


def compute_avg_llm_judge_metric(ice_score: Dict, code_judge: Dict) -> Optional[float]:
    """计算裁判模型指标平均值"""
    fc = ice_score["functional_correctness"]["score"]
    usefulness = ice_score["usefulness"]["score"]
    cj = code_judge["score"]
    if fc is None or usefulness is None or cj is None:
        return None
    return round((fc + usefulness + cj) / 3, 4)


# ==================== 主入口 ====================

def calculate_judge_model_metrics(
    feature_infos: List,
    code_blocks: str,
    code_answers: Optional[List] = None
) -> Dict[str, Any]:
    """
    计算基于第三方裁判模型的分级评估指标

    参数:
        feature_infos: 需求变更信息列表
        code_blocks:   模型生成的代码（字符串）
        code_answers:  参考答案列表（可选），格式同 origin_corpus["code_answers"]
    """
    problem = extract_problem_description(feature_infos)
    extract_code_blocks = extract_model_code_blocks(code_blocks)

    if not extract_code_blocks or not extract_code_blocks.strip():
        return {
            "avg_llm_judge_metric": None,
            "ice_score": None,
            "code_judge": None,
            "error": "模型输出代码为空"
        }

    reference = _build_reference(code_answers) if code_answers else None

    ice_score = compute_ice_score(problem, extract_code_blocks, reference)
    code_judge = compute_code_judge(problem, extract_code_blocks, reference)
    avg_llm_judge_metric = compute_avg_llm_judge_metric(ice_score, code_judge)

    return {
        "avg_llm_judge_metric": avg_llm_judge_metric,
        "ice_score": ice_score,
        "code_judge": code_judge,
        "error": None
    }


def _build_reference(code_answers: List) -> Optional[str]:
    """从 code_answers 列表构建参考代码字符串"""
    if not isinstance(code_answers, list):
        return None

    file_code_dict: Dict[str, str] = {}
    for answer_item in code_answers:
        if not isinstance(answer_item, dict):
            continue

        filepath = answer_item.get("filepath", "")
        snippet_code = answer_item.get("snippet_code", {})
        fix_type = answer_item.get("fix_type", "")

        if not filepath:
            continue

        code_content = ""
        checker = snippet_code.get("checker", []) if isinstance(snippet_code, dict) else []

        if isinstance(checker, list) and checker:
            blocks = [b for b in checker if isinstance(b, str)]
            code_content = "\n".join(blocks)
        elif isinstance(snippet_code, dict):
            code_block = snippet_code.get("code_block", "")
            if fix_type == "A" and code_block:
                code_content = code_block

        if code_content:
            file_code_dict[filepath] = code_content

    return "\n".join(file_code_dict.values()) if file_code_dict else None


def main():
    parser = argparse.ArgumentParser(
        description="计算基于第三方裁判模型的分级评估指标（ICE Score + Code Judge）"
    )
    parser.add_argument("--config", "-c", type=str, default="config.json",
                        help="配置文件路径（默认: config.json）")
    args = parser.parse_args()

    config = load_config(args.config)
    input_cfg = config.get("input", {})

    feature_infos = input_cfg.get("feature_infos")
    code_blocks = input_cfg.get("code_blocks")
    code_answers = input_cfg.get("code_answers")
    output_path = input_cfg.get("output")

    if not feature_infos or not code_blocks:
        log.error("配置文件中未指定 input.feature_infos 或 input.code_blocks")
        sys.exit(1)

    log.info(f"问题描述: {extract_problem_description(feature_infos)}")
    result = calculate_judge_model_metrics(feature_infos, code_blocks, code_answers)
    output_json = json.dumps(result, ensure_ascii=False, indent=2)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output_json)
        log.info(f"结果已写入: {output_path}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
