# DataMind 弹性大数据平台 — 方案总览

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v3.0 | 2026-05-11 | DataMind Team | 重新设计：基于剖面(Profile)的弹性框架，一套代码所有规模 |
| v3.1 | 2026-05-11 | DataMind Team | 重新定位：大批量数据流优先，交互查询次要 |

---

## 1. 项目定位

### 1.1 一句话

**DataMind 是一套可弹性伸缩的大数据全流程框架——核心解决大批量数据的采集、加工、分发问题，同一份代码，在笔记本上跑Demo，在云端支撑国际级业务。**

### 1.2 核心价值：数据流，不是数据查询

这个平台的首要用户场景不是"业务人员点按钮查一条数据"，而是：

| 场景 | 数据量 | 频率 | 典型消费者 |
|------|--------|------|-----------|
| 每日全量数据采集入库 | 百万~十亿行/天 | 定时 | 数据平台自身 |
| 批量ETL加工（清洗+关联+聚合） | TB级 | 定时 | 下游数据产品 |
| 批量数据导出给ML训练 | 百万行~TB级 | 按需 | ML工程师 |
| 批量数据同步给下游业务系统 | 百万行/次 | 定时/事件 | 业务系统 |
| 实时数据流订阅 | 万行/秒 | 持续 | 实时应用 |
| 交互式数据查询 | 千~万行/次 | 按需 | 分析师 |

**交互查询只是6个场景之一，且不是最重要的。** 之前的设计过度聚焦在交互查询上（Trino/ClickHouse），忽略了批量数据分发这个关键环节。

### 1.3 数据全流程：采集 → 加工 → 分发

```
                    ┌─────────────────────────────────────────────┐
                    │              DataMind 数据全流程              │
                    │                                             │
  数据源 ──采集──→ │  Raw → Cleaned → Detail → Summary → App     │ ──分发──→ 消费者
                    │         ↑                                   │
                    │         └── 治理（质量/血缘/安全）贯穿全流程    │
                    └─────────────────────────────────────────────┘

  采集(Ingest):  大批量数据从外部系统进入平台
  加工(Process): ETL清洗、关联、聚合、建模
  分发(Export):  加工后的数据从平台送出到消费者
  治理(Govern):  质量、血缘、安全贯穿全流程
  查询(Query):   交互式查询是分发的特例（小批量、低延迟）
```

### 1.4 核心创新

传统大数据方案的问题：Demo一套代码，生产一套代码，号称"迁移"但实为重写。

本方案的解法：

```
同一个代码库 → 选择不同的运行剖面(Profile) → 适配不同的规模
                    │
                    ├── dev: 笔记本, DuckDB, 本地文件, $0
                    ├── staging: 单台服务器, DuckDB, MinIO, ~$200/月
                    ├── prod: 集群, Spark, MinIO/S3, Kafka, ~$3,000/月
                    └── global: 多区域, Spark, S3, Kafka全球, ~$15,000/月
```

**不是"Demo代码→生产代码"的迁移，而是"同一份代码，profile不同"。**

### 1.3 与非弹性方案的对比

| 维度 | 传统方案 | 弹性框架 |
|------|---------|---------|
| Demo → 生产 | 重写基础设施层，40%复用 | 切换profile，业务代码100%复用 |
| 团队规模 | 架构为特定团队设计 | 架构不关心团队大小 |
| 规模扩展 | 重新选型、重新部署 | 在profile中加一行配置 |
| 能力激活 | 能力默认全开 | 按profile渐进激活 |
| 测试 | Demo和生产分开测试 | 同一套测试在所有profile上跑 |

### 1.4 诚实的"代码改动"承诺

"零代码改动"需要精确界定。以下是profile升级时**什么变、什么不变**的诚实清单：

| 组件 | dev→staging | staging→prod | 是否需要改动 |
|------|------------|-------------|-------------|
| dbt SQL模型（marts层） | 不变 | 不变 | ❌ 零改动 |
| dbt SQL模型（intermediate层） | 不变 | 内容从直通变为完整关联 | ⚠️ 模型文件存在，但内部逻辑通过`{% if %}`条件切换 |
| 数据质量规则YAML | 不变 | 不变（severity自动按profile生效） | ❌ 零改动 |
| Python ETL脚本 | 不变 | 不变 | ❌ 零改动 |
| FastAPI端点 | 不变 | 不变 | ❌ 零改动 |
| `config/profile.yaml` | 改1行 | 改1行 | ✅ 必须改 |
| dbt profiles配置 | 新增连接 | 新增连接 | ✅ 必须改 |
| 基础设施部署 | 新增MinIO等 | 新增Spark等 | ✅ 必须部署 |

**总结**：业务逻辑代码（SQL + Python + YAML规则）零改动。基础设施配置和部署必须改。这是诚实的承诺。

---

## 2. 弹性架构

### 2.1 三层抽象

```
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 2: 业务逻辑 ← 纯SQL + Python，不依赖任何基础设施               │
│  ──────────────────────────────────────────────────────────────────  │
│  · dbt models (SQL)         · Python transforms                     │
│  · Quality rules (YAML)     · Feature definitions (YAML)            │
│  · Data contracts (YAML)    · Metric definitions (YAML)            │
│  · Export definitions (YAML)· Ingestion configs (YAML)             │
│                                                                     │
│  ★ 这一层在所有profile下完全不变。不变 = 无需迁移 = 真正的弹性。        │
├──────────────────────────────────────────────────────────────────────┤
│  Layer 1: 抽象接口 ← Python接口，隔离业务逻辑和基础设施                │
│  ──────────────────────────────────────────────────────────────────  │
│  · IngestionInterface       · ComputeInterface                      │
│  · StorageInterface         · ExportInterface                       │
│  · MessageInterface         · SchedulerInterface                    │
│  · QueryInterface           · MetadataInterface                     │
│  · SecurityInterface        · ObservabilityInterface                │
│                                                                     │
│  ★ 业务代码只依赖接口，不依赖具体实现。                               │
├──────────────────────────────────────────────────────────────────────┤
│  Layer 0: 可插拔后端 ← 按profile选择具体实现，零代码改动              │
│  ──────────────────────────────────────────────────────────────────  │
│                                                                     │
│  Profile: dev               Profile: prod                           │
│  Ingestion: Python脚本       Ingestion: Airbyte+Canal+Debezium      │
│  Storage: LocalFS           Storage: S3/Iceberg                     │
│  Compute: DuckDBEngine      Compute: SparkEngine                    │
│  Export: LocalFileCopy      Export: S3Export+KafkaPublish+APIPush   │
│  Query: DuckDBEngine        Query: Trino/ClickHouse                 │
│  Scheduler: APScheduler     Scheduler: DagsterEngine                │
│                                                                     │
│  ★ 全部通过config/profile.yaml切换。                                │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 运行剖面（Profile）

| 剖面 | 场景 | 存储 | 计算 | 消息 | 调度 | 安全 | 典型硬件 | 月成本 |
|------|------|------|------|------|------|------|---------|--------|
| `dev` | 本地开发/Demo | LocalFS | DuckDB | — | Cron | — | 笔记本8GB | $0 |
| `staging` | 单机生产验证 | MinIO | DuckDB | — | Dagster | Basic | 1×16C64G | ~$200 |
| `prod` | 生产环境 | MinIO/S3 | Spark | Kafka | Dagster | Enterprise | 集群 | ~$3,000 |
| `global` | 多区域国际 | S3×3 | Spark×3 | Kafka×3 | Dagster×3 | ZeroTrust | 多集群 | ~$15,000 |

**剖面切换**：修改一个配置文件，重启服务。代码零改动。

```yaml
# config/profile.yaml — 唯一的切换点
profile: dev   # 改为 staging | prod | global

storage:
  backend: local_fs          # dev: local_fs | staging: minio | prod: s3
  root_path: ./data          # dev: ./data | prod: s3://datamind-prod/

compute:
  backend: duckdb            # dev: duckdb | prod: spark

scheduler:
  backend: apscheduler        # dev: apscheduler | prod: dagster
```

### 2.2.1 Profile切换机制：工厂模式

```python
# datamind/core/factory.py
import yaml
from pathlib import Path

def load_profile() -> dict:
    with open("config/profile.yaml") as f:
        return yaml.safe_load(f)

def get_storage() -> StorageInterface:
    config = load_profile()
    backend = config["storage"]["backend"]
    if backend == "local_fs":
        from datamind.backends.storage.local_fs import LocalFSBackend
        return LocalFSBackend(root_path=config["storage"]["root_path"])
    elif backend == "minio":
        from datamind.backends.storage.minio_fs import MinIOBackend
        return MinIOBackend(endpoint=config["storage"]["endpoint"])
    elif backend == "s3":
        from datamind.backends.storage.s3_fs import S3Backend
        return S3Backend(bucket=config["storage"]["bucket"])
    else:
        raise ValueError(f"Unknown storage backend: {backend}")

def get_compute() -> ComputeInterface:
    config = load_profile()
    backend = config["compute"]["backend"]
    if backend == "duckdb":
        from datamind.backends.compute.duckdb_engine import DuckDBEngine
        return DuckDBEngine()
    elif backend == "spark":
        from datamind.backends.compute.spark_engine import SparkEngine
        return SparkEngine(master=config["compute"]["master"])
    else:
        raise ValueError(f"Unknown compute backend: {backend}")

# 同理: get_scheduler(), get_auth(), get_observability() ...
```

**关键设计**：
1. 后端实现**延迟导入**（`import` 在函数内部），dev环境不需要安装Spark
2. 工厂函数根据 `profile.yaml` 自动选择后端
3. 业务代码只调用 `get_storage()` / `get_compute()`，不直接 `import` 任何后端
4. CI/CD中强制检查：业务代码不允许出现 `import duckdb` / `import boto3` / `from pyspark`

### 2.3 能力渐进激活

不是所有能力在所有剖面都激活。每个能力有最低剖面要求：

| 能力 | 最低剖面 | 理由 |
|------|---------|------|
| 数据采集(Ingestion) | dev | 核心能力，必须 |
| 批量ETL加工 | dev | 核心能力，必须 |
| 批量数据导出(Export) | dev | 核心能力，必须 |
| 数据质量检查 | dev | 核心能力，必须 |
| BI报表/大屏 | dev | 演示价值 |
| 交互式查询 | dev | DuckDB本地即可 |
| 元数据目录 | staging | 需要持久化元数据 |
| 数据血缘 | staging | 需要SQL解析引擎 |
| 质量门禁(block) | staging | 开发时不阻塞 |
| 数据API服务 | staging | 需要稳定服务 |
| 批量数据订阅(Kafka) | prod | 需要Kafka |
| 流处理(Flink) | prod | 需要Kafka+Flink |
| 列级脱敏 | prod | 生产安全 |
| 指标认证 | prod | 需要组织审批流 |
| ML平台 | prod | 需要稳定特征管线 |
| 多区域部署 | global | 需要多区域基础设施 |

**设计意图**：`dev`剖面下质量门禁只告警不阻塞，`prod`剖面下阻塞写入——同一份质量规则YAML，执行模式不同。

---

## 3. 框架扩展机制

### 3.1 纵向扩展（Scale Up：更好的机器）

```
dev: DuckDB + 4核笔记本 → staging: DuckDB + 64核服务器
                               │
                         同一份SQL, 同一份Parquet
                         只是CPU和内存更多
```

DuckDB天然支持——更多核自动并行，更大的内存自动缓存更多数据。

### 3.2 横向扩展（Scale Out：更多的机器）

```
staging: DuckDB + 单机MinIO
               │
               ▼  切换 profile: staging → prod
               │
prod: Spark + 分布式MinIO/S3 + Kafka
```

**切换要点**：

| 关注点 | 适配方式 |
|--------|---------|
| SQL方言 | dbt使用ANSI SQL子集，DuckDB和Spark都兼容。方言差异通过dbt宏适配 |
| 数据格式 | 统一Parquet，DuckDB和Spark原生支持 |
| 数据位置 | StorageInterface统一路径抽象，`data_path("cleaned/orders")`自动映射 |
| 消息传递 | 业务代码依赖MessageInterface，dev无消息直接跳过 |
| 调度 | 业务代码依赖SchedulerInterface，dev用APScheduler，prod用Dagster |
| 交互查询 | 业务代码依赖QueryInterface，dev用DuckDB，prod用Trino/ClickHouse |
| 数据采集 | 业务代码依赖IngestionInterface，dev用Python脚本，prod用Airbyte+Canal |
| 数据分发 | 业务代码依赖ExportInterface，dev用本地文件复制，prod用S3导出+Kafka发布+API推送 |

### 3.3 区域扩展（Scale Region：全球化）

```
prod: 1个区域 × S3 × Spark
           │
           ▼  切换 profile: prod → global
           │
global: 3个区域 × S3 × Spark, 全局元数据同步
```

**元数据是全局的，数据是本地的**：全球元数据目录（表名、Schema、血缘）跨区域同步，原始数据驻留在各区域。

---

## 4. 核心差异化

### 4.1 一式三杀

三个杀手级能力，`dev`剖面就能演示：

| 能力 | 一句话 |
|------|--------|
| 实时大屏 | 数据从入库到展示延迟<5秒 |
| 自然语言取数 | 业务人员用中文提问，3秒拿到结果 |
| 异常自动发现 | 平台主动发现异常并定位根因 |

### 4.2 弹性证明

同一个演示可以在5秒内切换剖面：

```bash
# Dev
$ export DATAMIND_PROFILE=dev
$ make demo

# Prod
$ export DATAMIND_PROFILE=prod
$ make demo    # ← 同一套代码，不同的基础设施
```

---

## 5. 叙事结构

对外讲弹性，对内讲剖面：

| 受众 | 叙事 |
|------|------|
| 决策者 | "一个框架，从笔记本到全球。不是先做Demo再重写，而是同一个系统逐步加资源。" |
| 技术团队 | "抽象层隔离基础设施，profile驱动后端选择。代码质量由测试保证，规模由profile保证。" |
| 运维团队 | "5个配置文件覆盖所有部署模式。加一个区域=加一行配置。" |

---

## 6. 文档导航

| 文档 | 内容 |
|------|------|
| [02-data-architecture.md](02-data-architecture.md) | 弹性数据架构、剖面驱动的数据分层、接口定义 |
| [03-data-governance.md](03-data-governance.md) | 剖面驱动的治理体系、渐进式质量门禁 |
| [06-tech-selection.md](06-tech-selection.md) | 可插拔后端选型矩阵、接口→实现映射 |
| [07-demo-implementation.md](07-demo-implementation.md) | dev剖面下的Demo实例化、最小但完整的实现 |
| [10-phased-roadmap.md](10-phased-roadmap.md) | 剖面升级路径：dev→staging→prod→global |

其余文档结构不变，理念对齐即可。

---

## 7. 术语表

| 术语 | 定义 |
|------|------|
| Profile（剖面） | 一组基础设施配置的组合，定义平台运行的规模层级 |
| Backend（后端） | 接口的具体实现，由profile驱动选择 |
| StorageInterface | 数据读写抽象，屏蔽本地/S3/MinIO差异 |
| ComputeInterface | SQL执行抽象，屏蔽DuckDB/Spark差异 |
| Scale Up | 纵向扩展：换更好的机器，同一份代码 |
| Scale Out | 横向扩展：加更多的机器，同一份代码 |
| Scale Region | 区域扩展：加更多的区域，同一份代码 |