# Judge Model Evaluator Skill

A specialized skill for evaluating code generation quality using standardized metrics including ICE Score and Code Judge assessments.

## Features

- **ICE Score Evaluation**: Measures functional correctness and usefulness
- **Code Judge Assessment**: Identifies inconsistencies in code implementation
- **Reference Comparison**: Enhanced accuracy when reference code is provided
- **Standardized Metrics**: Consistent scoring from 0-1 scale
- **Detailed Feedback**: Justifications and issue identification

## Quick Start

### Method 1: Using Configuration File

1. Create a `config.json` file:
```json
{
    "api": {
        "url": "your-api-endpoint",
        "key": "Bearer your-api-key",
        "model_name": "model-name"
    },
    "input": {
        "feature_infos": [{"变更描述": "Your requirements"}],
        "code_blocks": {"file.py": ["your code here"]},
        "code_answers": null
    }
}
```

2. Run evaluation:
```bash
python scripts/evaluate_code.py --config config.json
```

### Method 2: Direct Input

```bash
python scripts/evaluate_code.py \
  --requirements "Add user authentication" \
  --code "def authenticate_user(username, password): ..." \
  --reference "def authenticate_user(username, password): ..." \
  --api-url https://api.example.com \
  --api-key "Bearer your-key" \
  --model gpt-4
```

### Method 3: Using Files

```bash
python scripts/evaluate_code.py \
  --requirements-file requirements.txt \
  --code-file generated.py \
  --reference-file reference.py \
  --output results.json
```

## Environment Variables

You can set these instead of passing parameters:

- `JUDGE_API_URL`: API endpoint URL
- `JUDGE_API_KEY`: API authentication key
- `JUDGE_MODEL_NAME`: Model name to use
- `JUDGE_CONFIG_FILE`: Default config file path (default: config.json)

## Output Format

```json
{
  "avg_llm_judge_metric": 0.8333,
  "ice_score": {
    "functional_correctness": {
      "score": 0.75,
      "error": null,
      "justification": {...}
    },
    "usefulness": {
      "score": 1.0,
      "error": null,
      "justification": {...}
    }
  },
  "code_judge": {
    "score": 0.75,
    "inconsistencies": [...],
    "inconsistencies_count": 1,
    "error": null
  },
  "error": null
}
```

## Skill Structure

```
eval-code-evaluator/
├── SKILL.md              # Skill documentation and instructions
├── README.md             # This file
├── scripts/              # Executable scripts
│   ├── evaluate_code.py  # Easy-to-use wrapper script
│   └── judge_model_metrics_standalone.py  # Core evaluation logic
├── prompts/              # Evaluation prompt templates
│   ├── ice_score_*.jinja2
│   └── code_judge_*.jinja2
└── references/           # Documentation and examples
    └── config-example.json
```

## Dependencies

Install required packages:

```bash
pip install requests jinja2 loguru
```

## Supported Models

The skill works with any OpenAI-compatible API endpoint, including:
- OpenAI GPT models
- Anthropic Claude models
- Local models via Ollama or similar
- Custom deployed models

## Tips for Best Results

1. **Clear Requirements**: Be specific about expected functionality
2. **Complete Code**: Ensure the provided code is syntactically correct
3. **Reference Code**: When available, significantly improves evaluation accuracy
4. **Context**: Include relevant domain or project context
5. **Multiple Files**: For multi-file code, provide all related components

## Error Handling

Common errors and solutions:

- **API Connection Error**: Check API URL and key
- **Invalid Input**: Ensure requirements and code are provided
- **Template Not Found**: Verify prompts/ directory exists
- **JSON Parse Error**: Check config file format

## Integration Examples

### CI/CD Pipeline

```yaml
- name: Evaluate Code Quality
  run: |
    python scripts/evaluate_code.py \
      --requirements-file pr-requirements.md \
      --code-file src/new_feature.py \
      --reference-file tests/expected_feature.py \
      --output quality-report.json
```

### Python Integration

```python
from judge_model_metrics_standalone import calculate_judge_model_metrics

# Prepare inputs
feature_infos = [{"变更描述": "Implement user login"}]
code_blocks = {"auth.py": ["def login(username, password): ..."]}

# Run evaluation
results = calculate_judge_model_metrics(feature_infos, code_blocks)
print(f"Score: {results['avg_llm_judge_metric']}")
```