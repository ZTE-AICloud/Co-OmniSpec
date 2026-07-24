# interface_acquisition

接口获取模块，用于方式B（调用链扫描）的接口识别。**无 reverse 目录依赖**，完全集成在 OmniSpec2 代码库中。

## 依赖

- **Python 3.7+**
- **requests**：LLM 调用（`pip install requests`）

## 使用

```bash
# prepare：语法解析 + 语义解析（生成 call_tree_list.json、all_methods.json、all_functions.json）
python -m interface_acquisition.main --step prepare --input-base-dir {output_dir} --codebase {codebase}

# identify：接口识别（若前置依赖缺失且提供 --codebase，会先执行 prepare）
python -m interface_acquisition.main --step identify --input-base-dir {input_base_dir} [--codebase {codebase}]
```

## 环境变量（LLM）

- `OPENAI_API_URL` / `OPENAI_URL`：API 地址
- `OPENAI_API_KEY`：API Key
- `OPENAI_MODEL`：模型名称
- `OPENAI_MAX_CONCURRENT`：最大并发数

## 支持语言

当前仅支持 **Python**。如需 Java/C++/C，可扩展 `get_code_type` 与 `syntax_parser`。
