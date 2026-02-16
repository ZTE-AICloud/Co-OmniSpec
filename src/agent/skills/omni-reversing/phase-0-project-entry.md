# 阶段 0：分析项目入口

## 输入内容
当前目录代码结构

**输入说明**：
- 直接分析当前目录的代码文件
- 需要识别代码入口点并分析代码特征
- 重点查找主函数、入口文件、构建配置文件等

## 步骤
### 第一步：初始探索
- 首先列出目录和文件，获得结构的整体概览。
- 如果存在README文件（例如，README.md，README.txt），请先阅读它。
- 分析项目的构建文件，从以下维度进行深入分析：
    - **C/C++**：CMakeLists.txt（分析编译器设置、C++标准、依赖库、目标类型）、Makefile、configure.ac
    - **Python**：requirements.txt、pyproject.toml、setup.py、Pipfile、conda.yml（关注依赖版本、Python版本要求）
    - **JavaScript/Node.js**：package.json（scripts字段、dependencies、devDependencies、engines）、yarn.lock、package-lock.json
    - **Java**：pom.xml（Maven项目的依赖、插件、构建配置）、build.gradle（Gradle项目配置）、build.xml（Ant构建）
    - **Go**：go.mod（模块定义、依赖版本）、go.sum（依赖校验）
    - **Rust**：Cargo.toml（包信息、依赖、构建配置）、Cargo.lock
    - **容器化部署**：Dockerfile、docker-compose.yml、.dockerignore
    - **CI/CD配置**：.github/workflows/、.gitlab-ci.yml、Jenkinsfile、.travis.yml
    - **其他构建配置**：vcpkg.json、conanfile.txt、.bazelrc、ninja.build


### 第二步：入口文件查找
根据不同的语言类型，使用不同策略找到入口：
- **C/C++**：查找 `main()` 函数，排除测试文件（通常在 test/、tests/、*_test.cpp 中）
- **Python**：查找 `if __name__ == "__main__"` 或启动脚本
- **JavaScript/Node.js**：查看 package.json 的 main 字段或 index.js
- **Java**：查找包含 `public static void main()` 的类
- **Go**：查找 package main 和 main() 函数
- **Rust**：查找 src/main.rs 或 Cargo.toml 中的 [[bin]] 配置

找不到上述文件时，采用**检查特殊文件**模式：
- 查找包含"main"、"app"、"server"、"service"、 "entry"关键词的文件
- **通过目录结构推断**：
  * bin/、scripts/目录中的可执行文件
  * src/、app/、lib/目录中按文件大小和依赖关系排序

从入口文件开始，逐步阅读入口文件引用的其他文件，综合分析该入口处理外部系统的需求以及明确和其他系统的交互方式
交互方式参考以下形式：
- **函数回调 (Function Callback)**：通过注册回调函数响应事件或数据变化
- **REST API**：基于HTTP协议的RESTful接口，支持GET/POST/PUT/DELETE等操作
- **RPC (远程过程调用)**：如gRPC、Apache Thrift、Dubbo等，支持跨语言服务调用
- **GraphQL**：灵活的查询语言和API运行时，支持精确数据获取
- **WebSocket**：双向实时通信协议，常用于实时应用（聊天、推送、游戏）
- **消息队列**：异步通信机制
  * **Kafka**：高吞吐量分布式流处理平台
  * **RabbitMQ**：可靠的消息代理，支持多种消息模式
  * **Redis Pub/Sub**：轻量级发布订阅模式
  * **Apache Pulsar**：云原生分布式消息系统
- **事件驱动 (Event-Driven)**：基于事件发布订阅模式的松耦合架构
- **数据库交互**：
  * **SQL数据库**：MySQL、PostgreSQL、SQL Server、Oracle等
  * **NoSQL数据库**：MongoDB、Redis、Cassandra、DynamoDB等
  * **时序数据库**：InfluxDB、TimescaleDB等
- **文件系统交互**：本地文件读写、网络文件系统、对象存储（S3、OSS）
- **命令行接口 (CLI)**：通过命令行参数和标准输入输出进行交互
- **微服务间通信**：
  * **服务网格**：Istio、Linkerd等
  * **服务发现**：Consul、Eureka、Zookeeper等
  * **负载均衡**：Nginx、HAProxy、Envoy等
- **流处理**：Apache Kafka Streams、Apache Flink、Apache Storm等
- **批处理**：Apache Spark、Hadoop MapReduce、批处理脚本等
- **插件接口**：动态加载的扩展模块，支持功能插拔
- **中间件集成**：与各类中间件系统的集成接口


### 第三步：具体交互实现分析
基于已识别的交互方式，深入分析具体的实现细节：

**API接口实现分析**：
- **REST API**：查找路由定义、端点配置、HTTP方法映射
  * 搜索关键词：`@RequestMapping`、`@GetMapping`、`@PostMapping`、`app.get`、`app.post`、`router.`、`endpoint`
  * 查找API版本、URL路径、请求响应格式
- **RPC接口**：查找服务定义、方法签名、协议配置
  * 搜索关键词：`service`、`rpc`、`grpc`、`protobuf`、`.proto`文件
  * 分析服务注册、方法调用、错误处理机制

**消息交互实现分析**：
- **消息号/消息类型**：查找消息定义、消息ID、消息格式
  * 搜索关键词：`MSG_`、`MESSAGE_`、`msg_type`、`message_id`、`opcode`
  * 分析消息头部结构、消息体格式、消息路由规则
- **消息队列**：查找队列名称、主题配置、消费者注册
  * 搜索关键词：`queue`、`topic`、`producer`、`consumer`、`subscriber`
  * 分析消息序列化、持久化、重试机制

**回调接口实现分析**：
- **函数回调**：查找回调函数注册、事件监听器、钩子函数
  * 搜索关键词：`callback`、`listener`、`handler`、`hook`、`on_`、`register`
  * 分析回调触发条件、参数传递、异常处理
- **事件驱动**：查找事件定义、发布订阅机制、事件处理器
  * 搜索关键词：`event`、`emit`、`trigger`、`publish`、`subscribe`、`dispatch`

**协议和接口规范分析**：
- **协议定义**：查找协议规范、接口文档、数据格式定义
  * 搜索文件：`.proto`、`.thrift`、`.avsc`、`.yaml`、`.json`、`*.def`、`*.spec`
  * 分析协议版本、字段定义、编码规则
- **配置文件**：查找端口配置、服务发现、连接参数
  * 搜索关键词：`port`、`host`、`endpoint`、`url`、`address`、`config`
  * 分析超时设置、重连机制、负载均衡配置

**具体实现查找策略**：
1. **基于关键词搜索**：使用grep工具搜索相关关键词
2. **基于文件扩展名**：查找特定类型的配置文件和协议文件
3. **基于目录结构**：分析api/、handler/、service/、protocol/等目录
4. **基于代码注释**：查找包含接口说明、协议描述的注释
5. **基于配置文件**：分析配置文件中的服务配置、连接参数

### 第四步：整理输出

按照**输出格式**，整理所有项目入口信息：
- 存放到`omni-doc/specs-temp/intermediate/project-entry.md`

### 第五步：检查和验证

- 确认所有入口文件都已识别
- 验证交互方式的准确性
- 检查输出格式符合Markdown规范

## 分析要点

- **完整性**：确保所有入口点都已识别，不遗漏任何入口文件
- **准确性**：入口识别必须基于代码实际内容，不能主观推测
- **可追溯性**：每个入口都要明确对应的代码位置和交互方式

## 输出格式

```markdown
# 项目概览
- **项目类型**：[Application|Library|Mixed|Framework|Microservice]
- **主要编程语言**：[语言列表]
- **构建系统**：[CMake|Make|Maven|Gradle|npm等]
- **架构特点**：[单体|模块化|微服务|插件化等]
- **业务领域**：[电信通信|金融支付|电商零售|游戏娱乐|企业管理|物联网|人工智能|系统工具|Web服务|数据处理等]
- **关键技术栈**：[关键技术列表，如Spring、Hibernate、React、Angular、Vue、Docker、Kubernetes、Hadoop、Spark、TensorFlow等]

# 代码入口
1. {{api}}
- 描述: [处理外部系统需求的描述]
- 对外交互方式描述: [交互方式识别，如API调用|消息队列|RPC调用|HTTP请求|命令行交互|其他]
- 对外交互入口标识: [根据交互方式获取交互标识，如API链接|消息号|cmd命令|其他]
- 文件路径: {{file_path}}

## [交互方式2：如JOB入口]
[同上格式]

## [交互方式3：如消息队列]
[同上格式]

```
