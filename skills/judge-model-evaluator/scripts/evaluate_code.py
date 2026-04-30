#!/usr/bin/env python3
"""
Judge Model Evaluator - Easy-to-use wrapper for code evaluation

This script provides a simple interface to evaluate code generation quality
using ICE Score and Code Judge metrics.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add the parent directory to path to import the main module
sys.path.insert(0, str(Path(__file__).parent))

from judge_model_metrics_standalone import (
    load_config,
    calculate_judge_model_metrics,
    extract_problem_description,
    extract_model_code_blocks
)


def create_simple_config(api_url: str, api_key: str, model_name: str) -> Dict[str, Any]:
    """Create a minimal configuration for evaluation"""
    return {
        "api": {
            "url": api_url,
            "key": api_key,
            "model_name": model_name,
            "timeout": 60,
            "max_tokens": 16384,
            "temperature": 0.1
        }
    }


def evaluate_code_from_strings(
    requirements: str,
    generated_code: str,
    reference_code: Optional[str] = None,
    api_url: str = None,
    api_key: str = None,
    model_name: str = None
) -> Dict[str, Any]:
    """
    Evaluate code using string inputs

    Args:
        requirements: Natural language description of requirements
        generated_code: The code to evaluate
        reference_code: Optional reference/expected code
        api_url: API endpoint URL
        api_key: API authentication key
        model_name: Model name to use

    Returns:
        Evaluation results dictionary
    """
    # Load API configuration from environment or parameters
    config_file = os.environ.get('JUDGE_CONFIG_FILE', 'config.json')

    if os.path.exists(config_file):
        config = load_config(config_file)
    else:
        # Use provided parameters or environment variables
        api_url = api_url or os.environ.get('JUDGE_API_URL')
        api_key = api_key or os.environ.get('JUDGE_API_KEY')
        model_name = model_name or os.environ.get('JUDGE_MODEL_NAME')

        if not all([api_url, api_key, model_name]):
            raise ValueError(
                "API configuration not found. Please provide config.json or set "
                "JUDGE_API_URL, JUDGE_API_KEY, and JUDGE_MODEL_NAME environment variables"
            )

        config = create_simple_config(api_url, api_key, model_name)

    # Prepare inputs in the expected format
    feature_infos = [{"变更描述": requirements}]

    # Convert code string to expected format
    code_blocks = {"generated_code.py": [generated_code]}

    # Prepare reference code if provided
    code_answers = None
    if reference_code:
        code_answers = [{
            "filepath": "reference_code.py",
            "snippet_code": {
                "code_block": reference_code
            },
            "fix_type": "A"
        }]

    # Run evaluation
    return calculate_judge_model_metrics(feature_infos, code_blocks, code_answers)


def main():
    """Command line interface for the evaluator"""
    parser = argparse.ArgumentParser(
        description="Evaluate code generation quality using Judge Model metrics"
    )

    # Configuration options
    parser.add_argument("--config", "-c", type=str,
                        help="Configuration file path (default: config.json)")

    # Simple evaluation options
    parser.add_argument("--requirements", "-r", type=str,
                        help="Requirements description (natural language)")
    parser.add_argument("--code", type=str,
                        help="Generated code to evaluate")
    parser.add_argument("--reference", type=str,
                        help="Reference/expected code (optional)")

    # File-based options
    parser.add_argument("--requirements-file", type=str,
                        help="File containing requirements")
    parser.add_argument("--code-file", type=str,
                        help="File containing generated code")
    parser.add_argument("--reference-file", type=str,
                        help="File containing reference code")

    # API options
    parser.add_argument("--api-url", type=str,
                        help="API endpoint URL")
    parser.add_argument("--api-key", type=str,
                        help="API authentication key")
    parser.add_argument("--model", type=str,
                        help="Model name")

    # Output option
    parser.add_argument("--output", "-o", type=str,
                        help="Output file for results (default: stdout)")

    args = parser.parse_args()

    # Validate inputs
    if not args.config and not all([args.requirements or args.requirements_file,
                                   args.code or args.code_file]):
        parser.error("Must provide either --config or both requirements and code")

    try:
        # Method 1: Use config file directly
        if args.config:
            config = load_config(args.config)
            input_cfg = config.get("input", {})

            feature_infos = input_cfg.get("feature_infos")
            code_blocks = input_cfg.get("code_blocks")
            code_answers = input_cfg.get("code_answers")

            if not feature_infos or not code_blocks:
                parser.error("Config file must contain input.feature_infos and input.code_blocks")

            result = calculate_judge_model_metrics(feature_infos, code_blocks, code_answers)

        # Method 2: Use string inputs
        else:
            # Read requirements
            requirements = args.requirements
            if args.requirements_file:
                with open(args.requirements_file, 'r') as f:
                    requirements = f.read().strip()

            # Read generated code
            code = args.code
            if args.code_file:
                with open(args.code_file, 'r') as f:
                    code = f.read()

            # Read reference code
            reference = args.reference
            if args.reference_file:
                with open(args.reference_file, 'r') as f:
                    reference = f.read()

            result = evaluate_code_from_strings(
                requirements=requirements,
                generated_code=code,
                reference_code=reference,
                api_url=args.api_url,
                api_key=args.api_key,
                model_name=args.model
            )

        # Output results
        output_json = json.dumps(result, ensure_ascii=False, indent=2)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output_json)
            print(f"Results written to: {args.output}")
        else:
            print(output_json)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()