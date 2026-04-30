---
name: judge-model-evaluator
description: Evaluate code generation quality using third-party judge model metrics (ICE Score + Code Judge). Use this when the user needs to assess generated code quality, compare code outputs, or evaluate AI-generated code against requirements. This skill provides automated scoring for functional correctness, usefulness, and code consistency using LLM-based evaluation.
compatibility: Requires Python environment with requests, jinja2, loguru packages and access to LLM API endpoint
---
# Judge Model Evaluator Skill

This skill evaluates code generation quality using standardized metrics including ICE Score (Functional Correctness + Usefulness) and Code Judge assessments.

## When to Use

- Evaluating AI-generated code against requirements
- Assessing code quality in automated workflows
- Comparing multiple code implementations
- Getting structured feedback on code changes
- Validating that code meets specification requirements

## Quick Start

1. Ensure you have API access configured
2. Provide the requirement description and generated code
3. Optionally provide reference code for comparison
4. Get comprehensive evaluation scores

## What You Need to Provide

### Required Inputs

1. **Requirements/Feature Description** - What the code is supposed to do

   - Format: List of change descriptions or natural language requirements
2. **Generated Code** - The code to be evaluated

   - Format: String or structured code blocks with file paths

### Optional Inputs

3. **Reference Code** - Correct/expected implementation (if available)
   - Improves evaluation accuracy
   - Format: List of code answers with file paths and snippets

## Evaluation Metrics

### ICE Score Components

- **Functional Correctness (0-1)**: Does the code correctly implement the requirements?
- **Usefulness (0-1)**: Is the code practical and well-structured?

### Code Judge Components

- **Score (0-1)**: Overall code consistency and quality
- **Inconsistencies**: Detailed list of issues found
  - Severity levels: Small, Major, Fatal
- **Inconsistencies Count**: Number of issues found

### Overall Metric

- **Average LLM Judge Metric**: Combined score across all metrics

## Setup Instructions

### 1. Configure API Access

Create a configuration with your LLM API details:

```json
{
  "api": {
    "url": "your-api-endpoint",
    "key": "Bearer your-api-key",
    "model_name": "model-name",
    "timeout": 60,
    "max_tokens": 16384,
    "temperature": 0.1
  }
}
```

### 2. Install Dependencies

```bash
pip install requests jinja2 loguru
```

## Usage Examples

### Example 1: Basic Evaluation

**Input:**

- Requirements: "Add user authentication with JWT tokens"
- Generated Code: Python implementation of auth system

**Output:**

```json
{
  "avg_llm_judge_metric": 0.8333,
  "ice_score": {
    "functional_correctness": {"score": 0.75, ...},
    "usefulness": {"score": 1.0, ...}
  },
  "code_judge": {
    "score": 0.75,
    "inconsistencies": [...],
    "inconsistencies_count": 1
  }
}
```

### Example 2: With Reference Code

**Input:**

- Requirements: "Implement sorting algorithm"
- Generated Code: Bubble sort implementation
- Reference Code: Optimized quicksort

**Benefit:** More accurate evaluation with direct comparison

## Error Handling

The skill handles common errors gracefully:

- API connection failures
- Invalid input formats
- Template rendering errors
- JSON parsing issues

All errors are reported in the output with descriptive messages.

## Best Practices

1. **Provide Clear Requirements**: Be specific about what the code should do
2. **Include Context**: Add relevant domain information if needed
3. **Use Reference Code**: When available, significantly improves evaluation accuracy
4. **Check API Configuration**: Ensure proper API access before running
5. **Review Detailed Feedback**: Look at individual metric scores and justifications

## Template Files

The skill uses optimized prompt templates stored in `prompts/`:

- ICE Score templates for functional correctness and usefulness
- Code Judge templates with/without reference answers
- Both v1 and v2 variants for different evaluation strategies

## Output Interpretation

- **Scores close to 1.0**: Excellent implementation
- **Scores around 0.5-0.7**: Acceptable with room for improvement
- **Scores below 0.5**: Significant issues detected
- **Inconsistencies**: Detailed feedback for improvement

## Output template

评测结果

  代码已使用xx模型完成评测，以下是详细结果：

  📊 综合评分

  平均LLM评测指标:

- 功能正确性:
- 实用性:
- 代码一致性:

  🔍 详细分析

  功能正确性 (0.5/1.0)

  优点:

- xxx

  主要问题:

- xxx

  实用性 (0.75/1.0)

  优点:

- xxx

  主要问题:

- xxx

  代码一致性 (0.0/1.0)

   发现的不一致问题:

- xxx

  💡 改进建议

1. xxx
2. xxx

  总结：xxxx
