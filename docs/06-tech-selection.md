# DataMind 技术选型

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v1.0 | 2026-05-11 | DataMind Team | 初始版本 |
| v3.0 | 2026-05-11 | DataMind Team | 重写为弹性框架：profile驱动的可插拔后端矩阵 |

---

## 1. 选型原则

| 原则 | 含义 | 权重 |
|------|------|------|
| **开源优先** | 避免厂商锁定，成本可控，可定制 | 高 |
| **接口可替换** | 每个组件通过接口抽象，可按profile替换后端 | 高 |
| **渐进扩展** | 小规模能跑，大规模能扩，同一份代码 | 高 |
| **Python生态** | 数据领域Python人才最好找，生态最丰富 | 中 |
| **Parquet统一** | 所有数据以Parquet为通用格式，DuckDB/Spark原生支持 | 高 |

---

## 2. 可插拔后端矩阵

### 2.1 总览

| 接口 | dev | staging | prod | global |
|------|-----|---------|------|--------|
| **StorageInterface** | LocalFS | MinIO | S3/Iceberg | S3/Iceberg×3区域 |
| **ComputeInterface** | DuckDB | DuckDB | Spark | Spark×3区域 |
| **QueryInterface** | DuckDB | DuckDB | Trino / ClickHouse | Trino×3区域 / ClickHouse×3区域 |
| **MessageInterface** | NoopMessage | NoopMessage | Kafka | Kafka×3区域 |
| **SchedulerInterface** | APSchedulerBackend | DagsterScheduler | DagsterCluster | DagsterMultiRegion |
| **MetadataInterface** | SQLiteStore | PostgreSQLStore | OpenMetadataStore | MultiRegionMetadata |
| **IngestionInterface** | PythonScript | PythonScript+MinIO | Airbyte+Canal+Debezium | 每区域Airbyte+Canal |
| **AuthInterface** | NoAuth | OIDCAuth | OIDCAuth+MFA | FederatedAuth |
| **ObservabilityInterface** | StdoutObservability | FileObservability | PrometheusObservability | ThanosObservability |

### 2.2 每个接口的后端实现

#### StorageInterface

| 方法 | LocalFS (dev) | MinIO (staging) | S3 (prod/global) |
|------|---------------|-----------------|------------------|
| `read_parquet` | `duckdb.read_parquet('data/...')` | `minio.get_object()` → DuckDB | `boto3.get_object()` → Spark |
| `write_parquet` | `df.to_parquet('data/...')` | `minio.put_object()` | `df.write.parquet('s3://...')` |
| `exists` | `os.path.exists()` | `minio.stat_object()` | `boto3.head_object()` |
| `list_tables` | `os.listdir()` | `minio.list_objects()` | `boto3.list_objects_v2()` |

#### ComputeInterface

| 方法 | DuckDB (dev/staging) | Spark (prod/global) |
|------|---------------------|---------------------|
| `execute` | `duckdb.sql(sql)` | `spark.sql(sql)` |
| `register_table` | `CREATE VIEW AS SELECT * FROM read_parquet(path)` | `spark.read.parquet(path).createOrReplaceTempView(name)` |
| `collect` | `df.fetchall()` | `df.collect()` |

---

## 3. 关键技术决策

### 3.1 存储：Apache Iceberg + MinIO/S3

| 方案 | 优势 | 劣势 | 适合场景 |
|------|------|------|---------|
| 纯数据仓库 (Snowflake/BigQuery) | 开箱即用 | 贵，厂商锁定 | 预算充足 |
| 纯数据湖 (S3+Spark) | 灵活 | 无ACID/Schema | 数据量大 |
| **湖仓一体 (Iceberg+MinIO/S3)** | 兼具灵活性和ACID | 生态不如云服务 | **本项目的选择** |

选择Iceberg的理由：
1. Schema演进 — 加列/删列不需要重写数据
2. 时间旅行 — 可查询任意历史快照
3. ACID事务 — 并发写入不会不一致
4. 开放格式 — Parquet底层，DuckDB/Spark/Trino都能读
5. Profile弹性 — dev用本地Parquet，prod切Iceberg，dbt SQL不变

### 3.2 计算：DuckDB → Spark

| 方案 | 优势 | 劣势 | 适合规模 |
|------|------|------|---------|
| **DuckDB** | 嵌入式、零配置、单机碾压Spark | 不支持分布式 | <500GB |
| Apache Spark | 分布式、生态成熟 | 集群运维复杂、启动慢 | >100GB |

为什么DuckDB是dev/staging的最佳选择：
- 单机处理500GB以内，性能比Spark快3-5倍
- 零配置，`pip install duckdb`
- 直接读写Parquet，无需建表
- 与dbt完美集成（dbt-duckdb适配器）
- 数据量增长到TB级时，切换Spark（dbt-spark适配器）

### 3.3 ETL：dbt + Python

| 方案 | 优势 | 劣势 |
|------|------|------|
| **dbt** | SQL驱动、版本控制、测试内置 | 只做T(转换) |
| Apache Beam | 统一批流 | 学习曲线陡 |
| 自研Python | 完全可控 | 重复造轮子 |

分工：
- **dbt** — 80%结构化数据转换（SQL驱动，profile通过变量控制行为）
- **Python** — 20%复杂逻辑（ML特征、复杂解析、非结构化数据）
- **Dagster** — 编排dbt和Python任务（staging+ profile）

### 3.4 交互查询：DuckDB → Trino/ClickHouse（关键决策）

这是之前方案最大的遗漏。**批处理ETL和交互式查询是两个不同的场景，不应该用同一个引擎。**

| 场景 | 引擎 | 延迟要求 | 特点 |
|------|------|---------|------|
| 批处理ETL | Spark | 分钟级 | 吞吐量优先，启动延迟可接受 |
| 交互式查询 | Trino/ClickHouse | 秒级 | 延迟优先，启动必须快 |

如果用Spark做交互查询，用户点"查询"后要等5-10秒（Spark启动+调度），体验极差。

| 方案 | 优势 | 劣势 | 适用场景 |
|------|------|------|---------|
| **Trino** | 联邦查询（可查Iceberg/Hive/MySQL等）、SQL标准、社区活跃 | 无本地存储、纯计算 | 多数据源联邦查询 |
| **ClickHouse** | 极致OLAP性能、单表查询碾压级、国内社区活跃 | Join性能弱、运维复杂 | 单表大聚合、实时大屏 |
| **Apache Doris** | 兼容MySQL协议、Join性能好、国产 | 社区不如ClickHouse | 多表关联OLAP |
| **StarRocks** | Doris分支、性能更好 | 更新、社区较小 | 极致性能OLAP |

**选择策略**：

| profile | 交互查询引擎 | 理由 |
|---------|------------|------|
| dev | DuckDB | 单机性能足够，零配置 |
| staging | DuckDB | 单机性能足够，零配置 |
| prod | **Trino** | 联邦查询能力（Iceberg+MySQL+其他源），SQL标准 |
| prod（可选） | **ClickHouse** | 如果需要实时大屏和极致单表性能 |
| global | Trino + ClickHouse | Trino做联邦查询，ClickHouse做实时大屏 |

```
prod profile 完整架构:

数据源 → Kafka → Flink → Iceberg (S3)  ← Spark (批ETL读写)
                                    ↓
                              Trino (交互查询) → FastAPI → 前端
                              ClickHouse (实时大屏) → 大屏
```

### 3.5 流处理：Flink（prod+ profile）

| 方案 | 优势 | 劣势 | 适用profile |
|------|------|------|------------|
| 无 | 简单 | 无实时能力 | dev/staging |
| **Apache Flink** | 精确一次语义、状态管理、窗口计算 | 运维复杂 | prod+ |
| Spark Structured Streaming | 与Spark生态统一 | 延迟较高(秒级) | prod（备选） |

Flink在prod profile中的角色：
- 实时ETL：Kafka → Flink → Iceberg（分钟级延迟）
- 实时聚合：Kafka → Flink → ClickHouse（秒级延迟，供大屏消费）
- 实时告警：Kafka → Flink → 规则匹配 → 告警

### 3.6 数据采集：Python脚本 → Airbyte + Canal + Debezium

| 方案 | 优势 | 劣势 | 适用profile |
|------|------|------|------------|
| **Python脚本** | 简单、灵活 | 不可视化、难维护 | dev/staging |
| **Airbyte** | 200+连接器、UI配置、社区活跃 | 资源占用较大 | prod+ |
| **Canal** | 国内MySQL CDC标配、稳定 | 只支持MySQL | prod+（MySQL源） |
| **Debezium** | 支持多种数据库CDC | 配置复杂 | prod+（非MySQL源） |
| **DataX** | 国内广泛使用、阿里开源 | 只做批量、无CDC | prod+（可选） |

**国内环境推荐**：Canal（MySQL CDC）+ Airbyte（其他源）+ DataX（批量历史数据迁移）

### 3.7 调度：APScheduler → Dagster / Airflow

| 方案 | 优势 | 劣势 | 适用profile |
|------|------|------|------------|
| **APScheduler** | 纯Python，跨平台，零系统依赖 | 无UI，无依赖编排 | dev |
| **Dagster** | 数据感知调度、内置测试、现代UI | 社区比Airflow小 | staging+ |
| **Airflow** | 最主流、插件最多、社区最大 | 非数据感知、DAG编写繁琐 | staging+（备选） |

选择APScheduler作为dev调度器的理由：
- **跨平台** — Windows/macOS/Linux全部原生支持，不需要WSL
- **纯Python** — `pip install apscheduler`，与项目技术栈一致
- **进程内运行** — 不需要系统级守护进程，随FastAPI一起启动

Dagster vs Airflow 选择建议：
- **选Dagster**：如果团队以数据工程为主，重视数据资产视角和内置测试
- **选Airflow**：如果团队有Airflow经验，或需要大量现成Operator（如云服务集成）
- **两者都支持**：SchedulerInterface抽象了调度接口，可以随时切换

选择Dagster的理由：
- 软件定义资产（SDA）模型 — 每个数据表是一个资产
- 数据感知调度 — 上游更新自动触发下游
- 内置测试 — CI/CD友好
- Python原生 — 与dbt/Python无缝集成

### 3.5 治理：OpenMetadata（prod+ profile）

| 方案 | 优势 | 劣势 |
|------|------|------|
| **OpenMetadata** | 功能最全、UI最好、社区活跃 | 较新 |
| DataHub | 大厂背书 | 架构复杂 |
| 自研 | 完全定制 | 开发成本高 |

### 3.6 BI：Streamlit → Superset

| profile | BI工具 | 说明 |
|---------|--------|------|
| dev | Streamlit | 零配置，Python原生，适合Demo |
| staging+ | Superset | 开源免费，可视化丰富，支持大数据源 |

---

## 4. Profile技术栈详解

### 4.1 dev profile（$0/月）

| 层级 | 组件 | 选型 | 安装方式 |
|------|------|------|---------|
| 存储 | 文件存储 | 本地Parquet文件 | 无需安装 |
| 存储 | 元数据 | SQLite | Python内置 |
| 计算 | 分析引擎 | DuckDB | pip install |
| 加工 | 数据转换 | dbt-duckdb | pip install |
| 加工 | 复杂逻辑 | Python脚本 | 系统自带 |
| 加工 | 任务调度 | APScheduler | pip install |
| 服务 | 数据API | FastAPI | pip install |
| 服务 | 健康仪表盘 | Streamlit | pip install |
| 服务 | 实时大屏 | ECharts + Flask | pip install |
| 质量 | 数据验证 | SQL规则（dbt test） | 内置 |

**总内存需求：约2GB** | **总费用：$0**

### 4.2 staging profile（~$370/月）

| 层级 | 组件 | 选型 | 说明 |
|------|------|------|------|
| 存储 | 对象存储 | MinIO (Docker) | S3兼容 |
| 存储 | 元数据 | PostgreSQL (Docker) | 结构化元数据 |
| 计算 | 分析引擎 | DuckDB | 与dev相同 |
| 加工 | 数据转换 | dbt-duckdb | 与dev相同 |
| 加工 | 调度 | Dagster (Docker) | 数据感知调度 |
| 服务 | 数据API | FastAPI + Docker | 生产配置 |
| 服务 | BI | Superset (Docker) | 团队自助分析 |
| 治理 | 元数据 | 手动 + PostgreSQL | 基础目录 |
| 安全 | 认证 | Keycloak (Docker) | SSO |

### 4.3 prod profile（~$3,200/月）

| 层级 | 组件 | 选型 | 说明 |
|------|------|------|------|
| 存储 | 对象存储 | S3 | 数据湖底座 |
| 存储 | 表格式 | Apache Iceberg | ACID + Schema演进 |
| 计算 | 批处理引擎 | Apache Spark | 分布式批处理ETL |
| 计算 | 交互查询 | Trino | 秒级交互查询，联邦数据源 |
| 计算 | 实时大屏 | ClickHouse（可选） | 极致OLAP性能 |
| 消息 | 事件流 | Kafka | 流式数据解耦 |
| 计算 | 流处理 | Apache Flink | 实时ETL + 实时聚合 |
| 采集 | 批量 | Airbyte | 配置化数据接入 |
| 采集 | CDC(MySQL) | Canal | 国内MySQL CDC标配 |
| 采集 | CDC(其他) | Debezium | PostgreSQL/Oracle等CDC |
| 加工 | 数据转换 | dbt-spark | SQL驱动ETL |
| 加工 | 调度 | Dagster / Airflow (K8s) | 集群调度 |
| 治理 | 元数据 | OpenMetadata | 数据目录+血缘+质量 |
| 服务 | 数据API | FastAPI + K8s | 水平扩展 |
| 服务 | BI | Superset | 报表+自助分析 |
| 安全 | 认证 | OIDC + MFA | 企业安全 |
| 运维 | 容器 | K8s | 容器编排 |
| 运维 | 监控 | Prometheus + Grafana | 指标+告警 |

### 4.4 global profile（~$14,650/月）

在prod基础上增加：
- 每个区域独立部署一套prod基础设施
- 全局控制平面（元数据同步 + 权限统一 + 跨区域血缘）
- 数据驻留规则引擎（GDPR/CCPA/个保法）
- 跨区域监控聚合（Thanos + ELK多集群）
- HSM密钥管理

---

## 5. Profile升级路径

每个组件都有明确的升级路径，升级是"换后端"而非"重写业务逻辑"：

| 组件 | dev | staging | prod | 升级方式 |
|------|-----|---------|------|---------|
| 存储 | LocalFS | MinIO | S3/Iceberg | 改 `profile.yaml` 的 `storage.backend` |
| 批处理 | DuckDB | DuckDB | Spark | 改 `profile.yaml` 的 `compute.backend` + dbt adapter |
| 交互查询 | DuckDB | DuckDB | Trino/ClickHouse | 改 `profile.yaml` 的 `query.backend` |
| 调度 | APScheduler | Dagster/Airflow | Dagster/Airflow集群 | 改 `profile.yaml` 的 `scheduler.backend` |
| 采集 | Python脚本 | Python脚本 | Airbyte+Canal+Debezium | 改 `profile.yaml` 的 `ingestion.backend` |
| 元数据 | SQLite | PostgreSQL | OpenMetadata | 改 `profile.yaml` 的 `metadata.backend` |
| 认证 | NoAuth | OIDC | OIDC+MFA | 改 `profile.yaml` 的 `security.auth.backend` |
| BI | Streamlit | Superset | Superset+大屏 | 改 `profile.yaml` 的 `bi.backend` |

**核心原则：业务代码（dbt SQL + Python ETL + 质量规则）在所有profile下完全相同。**

---

## 6. SQL兼容性保证

### 6.1 兼容子集策略

业务SQL使用DuckDB和Spark的**交集**语法，方言差异通过dbt宏适配：

```sql
-- ✅ 兼容语法（DuckDB和Spark都支持）
SELECT
    DATE_TRUNC('month', order_time) AS order_month,
    SUM(amount) AS total_amount
FROM {{ ref('stg_orders') }}
WHERE order_status = 'completed'
GROUP BY 1

-- ⚠️ 方言差异通过宏适配
WHERE order_time >= {{ date_sub('CURRENT_DATE', 30) }}
```

### 6.2 dbt宏适配

```sql
-- macros/cross_dialect.sql
{% macro date_sub(date_expr, days) %}
    {% if target.type == 'duckdb' %}
        {{ date_expr }} - INTERVAL '{{ days }}' DAY
    {% elif target.type == 'spark' %}
        DATE_SUB({{ date_expr }}, {{ days }})
    {% endif %}
{% endmacro %}
```

---

## 7. 技术风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| DuckDB→Spark SQL不兼容 | 中 | 高 | dbt宏覆盖差异；CI在两个后端并行测试 |
| Iceberg生态不成熟 | 低 | 中 | Iceberg已被Apple/Netflix/Adobe大规模使用 |
| Dagster社区较小 | 中 | 低 | 核心功能稳定，必要时可切Airflow |
| dbt条件逻辑增加维护复杂度 | 中 | 中 | 限制条件逻辑只在intermediate层使用，marts层保持纯净 |
| Profile切换后行为不一致 | 中 | 高 | 跨profile自动化测试（见测试策略） |