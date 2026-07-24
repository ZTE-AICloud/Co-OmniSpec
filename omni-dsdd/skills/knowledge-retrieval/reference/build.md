# 知识库构建（build）—— knowledge-retrieval 的构建编排

> 本章定义 `knowledge-retrieval skill` 的完整构建流程。
> 由 SKILL.md 的 **build** 选项触发（按 `${CLAUDE_SKILL_DIR}/reference/build.md` 分步流程执行）。
>
> **三态触发**（互斥，用户显式选择）：
> - `--build [raw_knowledge_dir]`（首次构建）：全新建立向量索引 + graphify 图谱;可指定知识构建源目录路径（默认为当前目录`.`）。
> - `--build --update`（增量刷新）：向量增量、graphify 走 `--update`。
> - `--build --force`（强制重建）：向量 `--force` 重刷、graphify 删 `graphify-out` 后全新重建。
>
> **隔离设计**：依赖安装、graphify 安装检测、向量索引构建、环境探测、配置回填、校验收尾
> **全部在主线程执行**；**唯独「运行 graphify 构建 skill」这一步委托 `graphify-build`
> sub-agent 隔离执行**（graphify 是 skill，sub-agent 按 skill 方式跑、产物自动落盘）。
>
> **路径约定**：graphify 一律在**项目当前工作目录（cwd）**对 `.` 构建，产物固定落 `./graphify-out/`，
> 与检索时的读取位置严格一致。不再从 raw_knowledge_dir 拼绝对路径。

---

## 步骤 0 · 解析参数、探测模式、准备配置（主线程执行）

### 0.1 解析构建参数

触发形如：`--build [raw_knowledge_dir]` / `--build --update` / `--build --force`。
- 位置参数（可选）= 知识构建源目录 `<RAW_DIR>`，默认 `.`（项目根全部内容）。
- 三态互斥标志：无 / `--update` / `--force`。

记下：`<RAW_DIR>`（默认 `.`）、构建方式。

### 0.2 探测现状

```bash
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli --pretty config-info
```

- config 存在 → 读出 `mode` / `vector_index_exists` / `graph_exists` / `config_dir`。
- **config 不存在** → 走 0.3 创建后再探测。

### 0.3 创建 / 更新配置（本版本默认 baseline）

- **config 不存在**：以 `${CLAUDE_SKILL_DIR}/knowledge.config.yaml` 为模板，在**项目执行目录（根目录）**下创建，并把 `raw_knowledge_dir` 写为 0.1 解析出的 `<RAW_DIR>`。
- **config 已存在且本次传入了 `<RAW_DIR>`**：只更新 `raw_knowledge_dir` 字段，其余保持。

---

## 步骤 1 · 依赖检查与安装（主线程执行 · 仅构建时跑一次）

> knowledge-retrieval 自身脚本的 python 依赖（如 numpy / pyyaml / 嵌入库等），
> 集中在 `${CLAUDE_SKILL_DIR}/requirements.txt`。**只在构建流程装一次**（用户首次接入才构建），
> 检索路径不重复安装。graphify 自己的 python 依赖由步骤 2 的 graphify 安装脚本负责，二者分开。

```bash
# 安装 knowledge-retrieval 脚本依赖（幂等，已装则跳过/复用）
pip install -r "${CLAUDE_SKILL_DIR}/requirements.txt"
```

遇到distutils相关问题时（python版本大于3.12）：
尝试预升级 build 工具链

```bash
SETUPTOOLS_USE_DISTUTILS=local "<PY>" -m pip install --user --upgrade \
  pip setuptools wheel
```

---
## 步骤 2 · 安装 / 检查 graphify（主线程执行）
```bash
# 检测 graphify 是否可用
python -c "import graphify" 2>/dev/null || echo "NOT_FOUND"
```

- **已安装** → 跳过步骤2，进入步骤 3。
- **未安装** → 运行安装脚本：

```bash
# Linux / macOS
${CLAUDE_SKILL_DIR}/scripts/install_graphify.sh

# Windows
${CLAUDE_SKILL_DIR}\scripts\install_graphify.bat
# 验证
graphify --version
```


- **安装内容**：`graphify` + skill 注册。
- **平台参数**：默认注册 `claude-code`。

---

## 步骤 3 · 构建向量索引（主线程执行）

> 由 `mode` 自动路由粒度：enhance → attribute-level；baseline → chunk-level。无需手动指定 `--mode`。
> 向量索引**默认增量**（按内容 hash 复用），`--update` 与默认行为一致；**仅 `--force` 需显式重刷**。

```bash
# 后台启动构建
# --build / --build --update ：默认增量
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli build-vector-index \
    > .knowledge-cache/build.log 2>&1 &

# --build --force ：强制重刷（跳过增量缓存）
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli build-vector-index --force \
    > .knowledge-cache/build.log 2>&1 &
```

**构建等待说明：初次构建时，用户本地可能没有向量化模型，构建执行时会自动下载，耗时可能较长，以及若构建目标文件较多时，耗时也可能较长，请等待。**
构建过程可通过如下方式定期查看进度：
`cat .knowledge-cache/vectors/progress.json   # {"done":320,"total":1523,...}`
**返回示例**（成功时）：

```json
{
  "mode": "enhance",
  "total_entries": 1523,
  "encoded_new": 48,
  "reused_from_cache": 1475,
  "skipped": 0,
  "model": "BAAI/bge-base-zh-v1.5",
  "dim": 768
}
```


**产物**：`.knowledge-cache/vectors/matrix.npy`、`.knowledge-cache/vectors/manifest.json`（两模式共用）。


---

## 步骤 4 · 构建 graphify 图谱（主线程直接加载并运行 graphify skill）

> **路径约定**：
> - **cwd（执行目录）= 项目根**（步骤 0 的 `config_dir`）——graphify 产物固定落 cwd 的 `./graphify-out/`，
>   与检索读取位置严格一致。
> - **构建源 = `raw_knowledge_dir`**（步骤 0 读出，默认 `.` 即项目根全部内容；用户可指定项目内其他单一目录）。
> - graphify 是 **skill**，由主 agent 直接加载执行，**产物自动生成，无需手动搬运**。

**4.1 force 模式预处理（仅 `--force`，主线程执行）**

`--force` 时先删除项目根下旧图谱产物（产物始终落项目根，与构建源目录无关），再全新重建：

```bash
# 仅 --force 执行；<PROJECT_ROOT> = 步骤 0 的 config_dir
rm -rf "<PROJECT_ROOT>/graphify-out"
```

`--build` / `--update` 不删（update 靠 graphify 自身增量）。

**4.2 确认 cwd，然后主线程直接加载并运行 graphify skill**

先核对当前目录为项目根（步骤 0 的 `config_dir`），不是则 `cd` 过去——cwd 决定产物落点：

```bash
pwd   # 必须是 <PROJECT_ROOT>；否则先 cd "<PROJECT_ROOT>"
```

然后**由主 agent 直接加载 graphify skill 执行构建**（等价人工在项目根下执行 `/graphify <raw_knowledge_dir>`）：

- 构建方式 = `--build` / `--force` → 执行 `/graphify <raw_knowledge_dir>`
- 构建方式 = `--update`            → 执行 `/graphify <raw_knowledge_dir> --update`
（`<raw_knowledge_dir>` 用步骤 0 读出的值，默认 `.`。）

> **关于 API key / 语义抽取（重要，别被带偏）**：
> - graphify **不需要任何 API key**。代码文件走 AST 结构化抽取（无模型）；文档/论文/图片走语义抽取。
> - 语义抽取在**未设** `GEMINI_API_KEY` / `GOOGLE_API_KEY` 时，由 graphify skill **自行 dispatch
>   general-purpose sub-agent** 来充当 LLM（即用当前 Claude 抽取）——因为本步骤在主线程，这层
>   dispatch 能正常发起。**放手让 skill 按其 Step 3/Part B 的标准流程 dispatch 子 sub-agent 即可。**
> - **绝不要**因为缺 `GEMINI_API_KEY` / `GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`
>   而停下、索取或反复提示——那是对 graphify 的误读。graphify 也根本不读 openai/anthropic key。
> - graphify 内含较长 python 执行（抽取、聚类、落盘）与并行 sub-agent，属正常现象，耐心等 skill
>   完整跑完，不要中途判定卡死。

> - 构建方式映射：`--build` / `--force` → `/graphify <raw_knowledge_dir>`（force 已在 4.1 清空目录）；
>   `--update` → `/graphify <raw_knowledge_dir> --update`。
> - 产物（项目根 `graphify-out/` 下）：`graph.json`（检索用）、`graph.html`（可视化）、
>   `GRAPH_REPORT.md`（报告），均由 graphify skill 自动生成。

**运行后检查：对于用户指定了构建目录的情况下（即非默认目录 `.` 构建的情况，请确认构建输出 `graphify-out` 是否位于当前目录下，若构建结果存放到指定构建目录下（未存放于当前目录下），请将它复制到当前目录下，后续注册配置时请以当前目录下的 `graphify-out` 路径为准）**

**4.3 注册图谱路径到配置（graphify skill 成功跑完后，主线程执行）**

```bash
GRAPH_JSON="<PROJECT_ROOT>/graphify-out/graph.json"

PYTHONPATH="${CLAUDE_SKILL_DIR}" python -c "
import yaml, sys
config_path = sys.argv[1]
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
config.setdefault('retrievers', {})['graph'] = {'enabled': True, 'graph_path': sys.argv[2]}
with open(config_path, 'w') as f:
    yaml.safe_dump(config, f, allow_unicode=True)
print(f'已更新 graph_path: {sys.argv[2]}')
" "$(PYTHONPATH="${CLAUDE_SKILL_DIR}" python -c "from scripts.cli import get_config_path; print(get_config_path())")" "${GRAPH_JSON}"
```

- **enhance**：graphify 从构建源目录的 schema + instances + 文档抽取。
- **baseline**：graphify 从构建源目录的原始文档抽取。
- **两模式统一**：构建源都由 `raw_knowledge_dir` 决定，产物都落项目根 graphify-out。
-
---

## 步骤 5 · 校验与收尾（仅 enhance 模式执行，baseline跳过，主线程执行）

```bash
# 4.1 查看索引统计
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli stats

# 4.2 校验配置与知识库一致性
PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli validate
```

**`validate` 检查项**：config 合法性、`raw_knowledge_dir` 存在、schema/instances（enhance）、向量索引一致性（`matrix.npy` 与 `manifest.json` 版本匹配）。

---

## 人工运维速查

| 场景 | 命令 / 方式 |
|------|-------------|
| **首次构建** | `--build` |
| **增量刷新** | `--build --update`（向量增量 + graphify `--update`） |
| **强制重建** | `--build --force`（`rm -rf graphify-out` + 向量 `--force` + graphify 全新） |
| **仅强刷向量** | `PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli build-vector-index --force` |
| **查看模式/状态** | `PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli config-info` |
| **索引统计 / 校验** | `PYTHONPATH="${CLAUDE_SKILL_DIR}" python -m scripts.cli stats` / `validate` |
| **清理向量缓存** | `rm -rf .knowledge-cache/vectors/` |

---
> 若失败发生在图谱构建步骤，graphify skill 会在主线程直接报出关键错误，据此排查。
