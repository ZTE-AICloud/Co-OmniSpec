---
name: incremental-coverage
description: >
  仅针对增量（新增/修改）文件收集代码覆盖率。适用于功能分支覆盖率验证、TDD 第 7 步、
  implement 技能完成后、PR 需要覆盖率证据等场景。支持 C/C++、Java、Python、Go、  JavaScript/TypeScript、Rust，
  通过语言无关的流水线实现：
  识别变更文件 -> 开启覆盖率插桩 -> 运行目标测试 -> 提取过滤覆盖率 -> 生成可操作报告。
context: fork
---

# 增量代码覆盖率 (Agent Skill)

仅针对当前开发周期（分支、提交范围或工作区）中**变更的文件**收集、过滤并报告代码覆盖率。
通过将范围限定为增量变更，避免全量覆盖率的成本和噪声。

## 适用场景

- 功能实现后验证测试覆盖率（TDD 第 7 步）
- 为 Pull Request 或代码评审提供覆盖率证据
- 检查新增/修改代码是否有充分的测试覆盖
- 在 `implement` 技能完成后或 `springboot-verification` 中作为质量门禁
- 合并功能分支前验证覆盖率达标

### 不适用场景

- 为项目搭建初始覆盖率工具链（应使用 `cpp-testing`、`python-testing`、`golang-testing` 或 `rust-testing`）
- 运行全量项目覆盖率基线（本技能仅关注增量范围）
- 调试失败的测试（应使用对应语言的测试技能）
- 没有测试基础设施的项目

## 核心概念

- **增量范围**：仅与基准引用（默认 `origin/master` 或 `origin/main`）相比新增或修改的文件。
- **流水线模型**：识别 → 插桩 → 测试 → 提取 → 报告。每步独立，可单独重跑。
- **语言适配器**：流水线对所有语言通用，仅工具命令按语言切换。
- **覆盖率阈值**：增量文件默认 80% 行覆盖率，可配置。
- **源文件过滤**：收集全量运行数据后，过滤仅展示增量源文件（排除测试文件本身）。

## 流水线步骤

### 步骤 1：识别增量文件

确定哪些源文件（非测试文件）被新增或修改。

```bash
# 确定基准引用
BASE=$(git merge-base HEAD origin/master 2>/dev/null || git merge-base HEAD origin/main 2>/dev/null)

# 收集变更的源文件（排除测试文件和生成文件）
CHANGED_FILES=$(git diff --name-only --diff-filter=AM "$BASE" HEAD | \
  grep -E '\.(cpp|cxx|cc|c|h|hpp|java|py|go|ts|js|tsx|jsx|rs)$' | \
  grep -v -E '(test|spec|_test|_spec|Test|Spec)' | \
  grep -v -E '(vendor|node_modules|build|dist|__pycache__|target|\.generated\.)')

# 同时包含未跟踪的新文件
UNTRACKED=$(git ls-files --others --exclude-standard | \
  grep -E '\.(cpp|cxx|cc|c|h|hpp|java|py|go|ts|js|tsx|jsx|rs)$' | \
  grep -v -E '(test|spec|_test|_spec|Test|Spec)')

# 合并去重
ALL_CHANGED=$(echo -e "${CHANGED_FILES}\n${UNTRACKED}" | sort -u | sed '/^$/d')

echo "增量源文件："
echo "$ALL_CHANGED"
echo "---"
echo "合计：$(echo "$ALL_CHANGED" | wc -l) 个文件"
```

**决策点**：若 `ALL_CHANGED` 为空，输出"未检测到增量源文件，覆盖率检查不适用"并正常退出。

### 步骤 2：检测语言并选择适配器

检测项目的主要编程语言，选择对应的覆盖率工具。

| 识别标志 | 语言 | 覆盖率工具 | 插桩方式 |
|-----------|------|-----------|---------|
| `CMakeLists.txt` 或 `*.cmake` | C/C++ (GCC) | gcov + lcov | `-DENABLE_COVERAGE=ON` 或 `--coverage` |
| `CMakeLists.txt` + `clang++` | C/C++ (Clang) | llvm-cov | `-fprofile-instr-generate -fcoverage-mapping` |
| `pom.xml` 或 `build.gradle` | Java | JaCoCo | Maven: `jacoco-maven-plugin`；Gradle: `jacoco` 插件 |
| `setup.py`、`pyproject.toml`、`requirements.txt` | Python | pytest-cov | `pytest --cov` |
| `go.mod` | Go | go test -coverprofile | `go test -coverprofile=coverage.out` |
| `package.json`（含 `jest` 或 `vitest`） | JS/TS | Jest/Vitest `--coverage` | `--coverage --coverageReporters=text` |
| `Cargo.toml` | Rust | cargo-llvm-cov | `cargo llvm-cov` |

**多语言项目**：对每种检测到的语言分别运行适配器，按语言独立报告后汇总。

### 步骤 3：开启覆盖率插桩

按检测到的语言应用覆盖率插桩。仅在必要时重新编译。

#### C/C++ (GCC + CMake)

```bash
# 项目有覆盖率编译选项时
./build.sh fast cov notest

# 手动 CMake 方式：
cmake -S . -B build-cov -DENABLE_COVERAGE=ON -DCMAKE_BUILD_TYPE=Debug
cmake --build build-cov -j
```

#### C/C++ (Clang)

```bash
cmake -S . -B build-llvm -DENABLE_COVERAGE=ON -DCMAKE_CXX_COMPILER=clang++
cmake --build build-llvm -j
```

#### Java (Maven)

```bash
mvn test -DskipTests=false
mvn jacoco:report
```

#### Python

无需单独插桩步骤。`pytest-cov` 在测试运行时自动处理。

#### Go

无需单独插桩步骤。`go test -coverprofile` 在测试运行时自动处理。

#### JavaScript/TypeScript

无需单独插桩步骤。`--coverage` 标志在测试运行时自动处理。

#### Rust

```bash
cargo llvm-cov clean --workspace
```

### 步骤 4：运行目标测试

仅运行覆盖变更代码的测试，使用测试过滤器缩小范围。

#### 测试文件发现规则

将每个变更的源文件映射到对应的测试文件。

| 源文件模式 | 测试文件模式 |
|-----------|-------------|
| `src/foo.cpp` | `tests/test_foo.cpp` 或 `tests/foo_test.cpp` |
| `src/foo.py` | `tests/test_foo.py` |
| `src/foo.go` | `src/foo_test.go`（同包） |
| `src/foo.ts` | `src/foo.test.ts` 或 `tests/foo.test.ts` |
| `src/foo.rs` | `src/foo.rs`（内联 `#[cfg(test)]`）或 `tests/foo_test.rs` |
| `src/main/java/com/Foo.java` | `src/test/java/com/FooTest.java` |

**兜底方案**：若无法定位具体测试文件，提示用户手动指定要运行的测试，并报告当前未覆盖的增量文件列表。不运行全量测试套件。

#### C/C++

```bash
# 直接运行 GTest 二进制并过滤
./build-cov/test_binary --gtest_filter=ChangedSuite.*

# 通用 CTest
ctest --test-dir build-cov -R "TestPattern" --output-on-failure
```

#### Python

```bash
pytest tests/test_changed.py \
  --cov=src.changed_module \
  --cov-report=term-missing \
  --cov-report=html:coverage_html
```

#### Go

```bash
go test -coverprofile=coverage.out ./path/to/changed/package/...
go tool cover -func=coverage.out
```

#### Java

```bash
mvn test -Dtest=ChangedServiceTest
mvn jacoco:report
```

#### JavaScript/TypeScript

```bash
# Jest
npx jest --coverage --testPathPattern="changed.test"

# Vitest
npx vitest run --coverage test/changed.test.ts
```

#### Rust

```bash
cargo llvm-cov --lib -- changed_module
```

### 步骤 5：提取过滤覆盖率

提取覆盖率数据并过滤为仅增量源文件。

#### C/C++ (GCC)

**首选：lcov 文件过滤**

```bash
lcov --capture --directory build-cov --output-file coverage.info
lcov --extract coverage.info "${CHANGED_FILES[@]}" --output-file incremental.info
genhtml incremental.info --output-directory coverage_incremental
```

**兜底：直接使用 gcov**（当 lcov 因 Perl 模块缺失或版本兼容问题失败时）

```bash
# 逐文件生成 gcov 文本报告
for f in $(find build-cov -name '*.gcno'); do
  gcov -b -c "$f"
done

# 读取生成的 .gcov 文件
cat /tmp/ChangedFile.cpp.gcov
```

gcov 输出格式说明：
- `数字:` = 该行执行次数
- `#####:` = 该行**未被执行**
- `-:` = 不可执行行（注释、声明等）
- `*:` = 部分覆盖（宏展开，通常被 lcov filter 排除）

#### C/C++ (Clang)

```bash
llvm-profdata merge -sparse build-llvm/default.profraw -o build-llvm/default.profdata
llvm-cov report build-llvm/test_binary \
  -instr-profile=build-llvm/default.profdata \
  $(echo "$ALL_CHANGED" | tr '\n' ' ')
```

#### Java (JaCoCo)

```bash
mvn jacoco:report -Djacoco.dataFile=target/jacoco.exec
# 从 target/site/jacoco/index.html 中提取变更类的数据
```

#### Python

```bash
# --cov=module 在收集时即过滤；仅列出的模块出现在报告中
pytest --cov=src.module1 --cov=src.module2 \
  --cov-report=term-missing \
  --cov-report=html:coverage_incremental
```

#### Go

```bash
go tool cover -func=coverage.out | grep -E "$(echo "$ALL_CHANGED" | tr '\n' '|' | sed 's/|$//')"
```

#### JavaScript/TypeScript

```bash
npx jest --coverage --coverageReporters=json-summary
# 从 coverage/coverage-summary.json 中提取变更文件数据
```

#### Rust

```bash
cargo llvm-cov --summary-only | grep -E "$(echo "$ALL_CHANGED" | tr '\n' '|' | sed 's/|$//')"
```

### 步骤 6：生成报告

使用下方模板生成结构化报告。

## 报告模板

```text
## 增量覆盖率报告

**基准**: <基准提交或分支>
**目标**: <当前 HEAD>
**变更文件数**: <N> 个源文件（不含测试）
**语言**: <检测到的语言>
**覆盖率工具**: <工具名称及版本>

### 逐文件覆盖率

| 文件 | 总行数 | 已覆盖 | 未覆盖 | 行覆盖率% | 分支总数 | 已覆盖 | 分支覆盖率% | 状态 |
|------|--------|--------|--------|----------|---------|--------|------------|------|
| src/feature/new_module.cpp | 36 | 32 | 4 | 88.9% | 94 | 26 | 27.7% | PASS |
| src/feature/helper.py | 30 | 22 | 8 | 73.3% | 12 | 10 | 83.3% | FAIL |
| ... | ... | ... | ... | ... | ... | ... | ... | ... |

### 汇总

- **增量总行数**: X
- **已覆盖行数**: Y
- **整体增量覆盖率**: Z%
- **阈值**: 80%
- **结论**: PASS / FAIL

### 未覆盖行（可操作项）

- `src/feature/helper.py:15-22` -- `process_data()` 中的错误处理分支
- `src/feature/new_module.cpp:89` -- `validate()` 中的空值检查

### 改进建议

1. 为 `helper.py:process_data()` 的错误路径添加测试（第 15-22 行）
2. 为 `new_module.cpp:validate()` 的空输入边界添加测试（第 89 行）
```

## 语言适配器速查表

| 语言 | 插桩方式 | 运行测试 | 覆盖率数据 | 增量过滤 | 报告生成 |
|------|---------|---------|-----------|---------|---------|
| **C/C++ (GCC)** | CMake `--coverage` 或 `-DENABLE_COVERAGE=ON` | `ctest` 或 `./test --gtest_filter=` | `.gcno`/`.gcda` | `lcov --extract` 或 `gcov -b -c` | `genhtml` 或 gcov 文本 |
| **C/C++ (Clang)** | `-fprofile-instr-generate -fcoverage-mapping` | `ctest` 或 `./test` | `.profraw`/`.profdata` | `llvm-cov report <files>` | `llvm-cov report` |
| **Java** | JaCoCo 插件 | `mvn test -Dtest=` | `jacoco.exec` | JaCoCo CLI 过滤或 XML 解析 | `target/site/jacoco/` |
| **Python** | 无（运行时） | `pytest --cov=module` | `.coverage` | `--cov=module1 --cov=module2` | `--cov-report=term-missing` |
| **Go** | 无（运行时） | `go test -coverprofile=` | `coverage.out` | `go tool cover -func=` + grep | `go tool cover -html=` |
| **JS/TS** | 无（运行时） | `npx jest --coverage` | `coverage/coverage-final.json` | `--collectCoverageFrom=` | `--coverageReporters=text` |
| **Rust** | `cargo llvm-cov` | `cargo llvm-cov` | lcov 输出 | `cargo llvm-cov` + grep | `cargo llvm-cov --html` |

## 常见问题

### 覆盖率工具兼容性

- **gcno 版本不匹配**：编译使用的 GCC 版本必须与 gcov 版本一致，否则 `.gcno` 文件无法读取。
  **解决方案**：使用同一 GCC 安装的 `gcov -b -c` 直接处理。

- **lcov Perl 模块缺失**：lcov 依赖 `IO::Uncompress::Gunzip`、`Digest::MD5` 等 Perl 模块，
  在精简环境中可能缺失。
  **解决方案**：通过 `cpanm` 安装，或直接使用 `gcov` 兜底。

- **Clang profile 数据未生成**：必须正确设置 `LLVM_PROFILE_FILE` 环境变量。
  在运行测试前显式指定路径。

### 构建系统问题

- **覆盖率标志未生效**：CMake 会缓存编译标志。若之前未启用覆盖率编译，必须先清理构建目录。
  ```bash
  rm -rf build-cov && cmake -S . -B build-cov -DENABLE_COVERAGE=ON
  ```

- **测试文件未被发现**：新增测试文件必须位于构建系统实际扫描的目录中
  （CMake 的 `GLOB_RECURSE`、Maven 的 `src/test/java` 等）。
  glob 范围外的文件会被静默排除。

- **`--coverage` 链接报错**：该标志必须同时应用于编译**和**链接选项。
  缺少链接标志会导致 `__gcov_init` 未定义引用。

### 覆盖率数据问题

- **lcov extract 结果为空**：覆盖率数据中的路径可能是绝对路径，而过滤模式使用相对路径（或反之）。
  使用 `lcov --list coverage.info` 查看数据中的实际路径。

- **头文件覆盖率为 0%**：部分工具仅对 `.cpp`/`.c` 文件插桩。纯头文件代码需要被已覆盖的源文件
  `#include`，或使用 Clang 的 `-fcoverage-mapping`。

- **测试文件被计入源文件**：必须从覆盖率指标中排除测试文件——测试文件天然 100% 执行覆盖，
  但不代表生产代码质量。

### 测试执行问题

- **测试通过但覆盖率为 0%**：二进制可能未使用覆盖率标志重新编译。从头重新编译。

- **不稳定测试导致覆盖率缺口**：崩溃的测试可能未写入 `.gcda`/`.profraw` 数据。
  在信任覆盖率数据前先稳定测试。

## SDD / TDD 集成

### 作为 TDD 第 7 步（覆盖率验证）

在 TDD 工作流中调用时：
1. 以当前任务中修改的文件作为增量范围
2. 仅度量包含新增/修改代码的函数或文件的覆盖率
3. 不度量全量项目覆盖率
4. 按 80% 阈值报告结果

### 从 `implement` 技能调用

在 implement 技能结束时调用本技能，验证所有增量变更文件达到覆盖率阈值。
报告作为最终任务执行报告的一部分。

### 从评审阶段调用

在代码评审或验证循环中，本技能提供限定在 PR 变更范围内的覆盖率证据。

## 最佳实践

### 应该做的

- 首次在构建目录启用覆盖率时，务必清理并重新编译
- 仅过滤源文件（排除测试、生成代码、第三方代码）
- 先将变更文件映射到测试文件并运行目标测试，无法映射时再运行全量套件
- 报告未覆盖行时附带 `文件:行号` 引用，便于跟进
- git diff 使用 `--diff-filter=AM` 聚焦新增和修改文件（排除已删除文件）
- C/C++ 使用 Debug 优化级别（`-O0` 或 `-Og`）运行覆盖率

### 不应该做的

- 仅需增量数据时不要运行全量项目覆盖率（太慢、噪声太多）
- 不要将测试文件计入覆盖率百分比
- 不要跨不同编译器版本或标志组合比较覆盖率百分比
- 不要信任优化构建（`-O2`/`-O3`）的覆盖率数据——编译器可能内联或消除代码路径
- 不要跳过 git diff 识别步骤，凭猜测判断哪些文件变更了

## 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--base` | `origin/master` 或 `origin/main` | 对比的 Git 引用 |
| `--threshold` | `80` | 通过的最低覆盖率百分比 |
| `--include-untracked` | `true` | 包含未跟踪（新建）文件 |
| `--exclude-pattern` | `(test\|spec\|_test\|_spec\|vendor\|build\|dist\|node_modules\|__pycache__\|target\|.generated.)` | 排除文件的正则模式 |
| `--report-format` | `text` | 输出格式：`text`、`json`、`html` |

## 输出

### 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 覆盖率达到或超过阈值 |
| 1 | 覆盖率低于阈值 |
| 2 | 流水线错误（构建失败、工具未找到等） |
| 3 | 未检测到增量文件（非错误） |

## 示例

### C++/CMake 项目

```bash
# 步骤 1：识别变更
BASE=$(git merge-base HEAD origin/master)
CHANGED=$(git diff --name-only --diff-filter=AM "$BASE" HEAD | \
  grep -E '\.(cpp|h)$' | grep -v -E 'test|Test')

# 步骤 2-3：开启覆盖率编译
./build.sh fast cov notest

# 步骤 4：运行目标测试
./build-cov/test_binary --gtest_filter=ChangedSuite.*

# 步骤 5：提取并过滤
if lcov --capture --directory build-cov --output-file coverage.info 2>/dev/null; then
  lcov --extract coverage.info ${CHANGED} --output-file incremental.info
  genhtml incremental.info --output-directory coverage_incremental
else
  # 兜底：直接使用 gcov
  for gcno in $(find build-cov -name '*.gcno'); do
    gcov -b -c "$gcno" 2>/dev/null
  done
fi
```

### Python 项目

```bash
# 识别变更模块
CHANGED_MODULES=$(git diff --name-only --diff-filter=AM origin/master HEAD | \
  grep '\.py$' | grep -v test | sed 's|/|.|g; s|\.py$||')

# 仅对变更模块运行覆盖率
pytest --cov=$(echo "$CHANGED_MODULES" | head -1 | sed 's|\..*||') \
  --cov-report=term-missing \
  --cov-report=html:coverage_incremental
```

### Go 项目

```bash
# 识别变更包
CHANGED_PKGS=$(git diff --name-only --diff-filter=AM origin/master HEAD | \
  grep '\.go$' | grep -v _test | xargs dirname | sort -u)

# 逐包运行覆盖率
for pkg in $CHANGED_PKGS; do
  go test -coverprofile="cov_$(echo $pkg | tr '/' '_').out" "./$pkg/..."
done

# 输出汇总
for f in cov_*.out; do
  go tool cover -func="$f"
done
```

## 备注

- 本技能是对各语言测试技能（`cpp-testing`、`python-testing`、`golang-testing`、`rust-testing`）
  的**补充**而非替代。初始覆盖率工具链搭建或详细测试编写指南请参考对应技能。
- 80% 阈值与 `tdd-workflow` 技能的覆盖率要求保持一致。
- 当 `lcov` 失败时（在受限环境中常见），`gcov -b -c` 兜底方案可直接提供基础逐函数覆盖率数据，
  无需重新运行测试。
