# DataMind 弹性数据架构

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v3.0 | 2026-05-11 | DataMind Team | 重新设计：剖面驱动的弹性数据分层、统一接口定义 |

---

## 1. 架构原则

| 原则 | 含义 | 首次在哪个剖面强制执行 |
|------|------|---------------------|
| 数据不丢失 | 每条记录可追踪：ingested = processed + errored | dev |
| 代码管分层 | 分层索引由dbt目录树管理，不由运维手工维护 | dev |
| 格式统一 | 所有转换产出为Parquet，DuckDB和Spark原生支持 | dev |
| 幂等写入 | 所有ETL可安全重跑，产出一致 | staging |
| ACID保障 | 生产写入需要事务保证 | prod（Iceberg） |
| 字段级血缘 | 每个字段可追溯到源头 | staging |

---

## 2. 数据分层模型

### 2.1 统一五层模型（所有profile一致）

**核心原则：所有profile使用完全相同的dbt ref()链。** 差异不在"有没有这一层"，而在"这一层做什么"。

```
所有profile统一5层:

Raw ─────────┐
             │
Cleaned ─────┤    ← dev: 简单格式化    prod: 完整清洗+编码统一+空值处理
             │
Detail ──────┤    ← dev: 直通(1:1)     prod: 维度关联+业务解码+去重
             │
Summary ─────┤    ← dev: 简单聚合      prod: 口径统一+多维度聚合
             │
App ──────────┘    ← 所有profile: 面向业务主题的宽表/星型模型
```

**为什么不能跳层？** 如果dev跳过Detail层，marts的`ref()`就要指向`stg_orders`；而prod的marts指向`int_order_detail`。这意味着**同一份SQL必须写两个版本**，"零代码改动"就是谎言。因此，所有层在所有profile下都必须存在，只是复杂度不同。

**声明方式**：分层由dbt目录树声明，所有profile共用同一棵目录树：

```
dbt/models/                    ← 所有profile共用
├── staging/                   ← Raw → Cleaned
├── intermediate/              ← Cleaned → Detail
├── marts/                     ← Detail → Summary → App
│   ├── finance/
│   └── product/
```

**dev vs prod 的差异在模型内容，不在模型结构**：

```sql
-- models/intermediate/int_order_detail.sql

-- dev profile: 直通（1:1映射，不做复杂关联）
{{ config(materialized='table') }}

SELECT
    order_id,
    customer_id,
    product_id,
    amount,
    order_time
FROM {{ ref('stg_orders') }}

-- prod profile: 完整关联（维度表JOIN + 业务解码 + 去重）
-- 通过 dbt macro 实现 profile 条件逻辑：
{{ config(materialized='incremental') }}

SELECT
    o.order_id,
    o.customer_id,
    c.customer_state,
    c.customer_city,
    o.product_id,
    p.product_category_name,
    o.amount,
    o.order_time,
    o.order_status,
    CASE o.order_status
        WHEN 'delivered' THEN '已完成'
        WHEN 'shipped' THEN '配送中'
        ELSE '其他'
    END AS order_status_desc
FROM {{ ref('stg_orders') }} o
LEFT JOIN {{ ref('stg_customers') }} c ON o.customer_id = c.customer_id
LEFT JOIN {{ ref('stg_products') }} p ON o.product_id = p.product_id
WHERE o.order_id IS NOT NULL
```

**实现方式**：使用dbt变量控制模型行为，而非跳过模型：

```yaml
# dbt_project.yml — 按profile设置变量
vars:
  datamind_profile: "{{ env_var('DATAMIND_PROFILE', 'dev') }}"
  detail_layer_mode: "{{ 'full' if var('datamind_profile') in ['prod', 'global'] else 'passthrough' }}"
```

```sql
-- models/intermediate/int_order_detail.sql — 条件逻辑
{% if var('detail_layer_mode') == 'passthrough' %}
-- dev: 直通
SELECT order_id, customer_id, product_id, amount, order_time
FROM {{ ref('stg_orders') }}

{% else %}
-- prod: 完整关联
SELECT
    o.order_id,
    o.customer_id,
    c.customer_state,
    ...
FROM {{ ref('stg_orders') }} o
LEFT JOIN {{ ref('stg_customers') }} c ON ...
LEFT JOIN {{ ref('stg_products') }} p ON ...
{% endif %}
```

**关键保证**：下游模型（marts）的 `ref('int_order_detail')` 在所有profile下都能解析。

### 2.2 层定义

| 层 | 输入 | 输出 | 职责 | dev行为 | prod行为 |
|----|------|------|------|---------|---------|
| Raw | 数据源 | Parquet文件 | 原样保存，添加采集元数据(_ingested_at, _source) | 同 | 同 |
| Cleaned | Raw | Parquet文件 | 格式统一、编码统一、空值处理 | 简单格式化（类型转换+空值填充） | 完整清洗+编码统一+异常值处理 |
| Detail | Cleaned | Parquet文件 | 维度关联、业务解码、去重 | 直通（1:1映射，不做关联） | 完整维度JOIN+业务解码+去重 |
| Summary | Detail | Parquet文件 | 聚合、降维、口径统一 | 简单聚合（GROUP BY + SUM） | 口径统一+多维度+同比环比 |
| App | Summary/Detail | Parquet文件 | 面向业务主题的宽表/星型模型 | 同 | 同 |

---

## 3. 统一接口层

### 3.1 StorageInterface

业务代码不直接读写文件或S3，通过StorageInterface：

```python
from datamind.interfaces.storage import StorageInterface

class StorageInterface:
    """统一数据读写抽象"""

    def read_parquet(self, path: str) -> DataFrame:
        """读Parquet文件，path是逻辑路径如 'cleaned/orders' """
        ...

    def write_parquet(self, df: DataFrame, path: str, mode: str = 'overwrite'):
        """写Parquet文件"""
        ...

    def exists(self, path: str) -> bool:
        """检查路径是否存在"""
        ...

    def list_tables(self, zone: str) -> list[str]:
        """列出某层的所有表"""
        ...

    def get_size(self, path: str) -> int:
        """获取数据大小"""
        ...

    def delete(self, path: str):
        """删除数据"""
        ...
```

**后端实现映射**：

| StorageInterface方法 | LocalFS (dev) | MinIO (staging) | S3 (prod/global) |
|---------------------|---------------|-----------------|------------------|
| `read_parquet` | `open('data/...')` | `minio.get_object()` | `boto3.get_object()` |
| `write_parquet` | `open('data/...', 'w')` | `minio.put_object()` | `boto3.put_object()` |
| `exists` | `os.path.exists()` | `minio.stat_object()` | `boto3.head_object()` |
| `list_tables` | `os.listdir()` | `minio.list_objects()` | `boto3.list_objects()` |

### 3.2 ComputeInterface

```python
from datamind.interfaces.compute import ComputeInterface

class ComputeInterface:
    """统一SQL执行抽象"""

    def execute(self, sql: str) -> DataFrame:
        """执行SQL，返回DataFrame"""
        ...

    def register_table(self, name: str, path: str):
        """注册表（创建视图或临时表）"""
        ...

    def collect(self, df: DataFrame) -> list[dict]:
        """收集结果到Python列表"""
        ...

    def explain(self, sql: str) -> str:
        """获取执行计划"""
        ...
```

**后端实现映射**：

| ComputeInterface方法 | DuckDB (dev/staging) | Spark (prod/global) |
|---------------------|---------------------|---------------------|
| `execute` | `duckdb.sql(sql)` | `spark.sql(sql)` |
| `register_table` | `CREATE VIEW AS SELECT * FROM read_parquet(path)` | `spark.read.parquet(path).createOrReplaceTempView(name)` |
| `collect` | `df.fetchall()` | `df.collect()` |

### 3.3 ExportInterface（数据分发）

数据不只是"进来"和"查出来"，还要"送出去"。ExportInterface 是之前方案最大的遗漏。

```python
from datamind.interfaces.export import ExportInterface

class ExportInterface:
    """统一数据分发抽象"""

    def export_file(self, source_path: str, target_config: dict) -> str:
        """导出数据到文件（Parquet/CSV/JSON）"""
        ...

    def export_api(self, source_path: str, target_config: dict) -> str:
        """推送数据到外部API"""
        ...

    def export_stream(self, source_path: str, topic: str) -> str:
        """发布数据到消息流（Kafka）"""
        ...

    def create_snapshot(self, source_path: str, snapshot_config: dict) -> str:
        """创建数据快照（供下游系统拉取）"""
        ...

    def list_exports(self, source_path: str = None) -> list[dict]:
        """列出所有导出任务"""
        ...
```

**后端实现映射**：

| ExportInterface方法 | LocalExport (dev) | S3Export (prod) | KafkaExport (prod+) |
|--------------------|--------------------|-----------------|---------------------|
| `export_file` | `shutil.copy2()` 到目标目录 | `boto3.copy()` 到目标bucket | N/A |
| `export_api` | `requests.post()` | `requests.post()` + 重试 | N/A |
| `export_stream` | 无（跳过） | 无（跳过） | `kafka_producer.send()` |
| `create_snapshot` | 复制到 `snapshots/` 目录 | Iceberg快照 + 生成manifest | Iceberg快照 |

**数据分发场景矩阵**：

| 消费者 | 分发方式 | 数据量 | 延迟要求 | profile |
|--------|---------|--------|---------|---------|
| ML训练 | 文件导出(Parquet) | 百万~十亿行 | 无（批量） | dev+ |
| 报表系统 | 文件导出(CSV) | 万~百万行 | 无（批量） | dev+ |
| 下游业务DB | API推送 | 万~百万行 | 分钟级 | staging+ |
| 实时应用 | Kafka流订阅 | 万行/秒 | 秒级 | prod+ |
| 第三方系统 | S3共享 | 百万行 | 小时级 | prod+ |
| 分析师 | 交互查询(Trino) | 千~万行 | 秒级 | prod+ |

**导出配置声明**：

```yaml
# config/exports.yaml — 所有profile共用
exports:
  - name: ml_training_orders
    source: app/app_daily_revenue
    format: parquet
    target: file                    # dev: file, prod: s3
    target_path: ml/feature_store/orders
    schedule: "0 6 * * *"           # 每天早上6点导出
    partition_by: ["order_month"]

  - name: realtime_order_stream
    source: detail/int_order_detail
    format: stream
    target: kafka                   # prod+ only
    topic: orders.detail
    trigger: on_change              # 数据变更时触发

  - name: daily_report_csv
    source: app/app_daily_revenue
    format: csv
    target: file
    target_path: reports/daily
    schedule: "0 8 * * *"
    filters:
      - field: order_month
        op: ">="
        value: "CURRENT_MONTH"
```

### 3.4 接口使用示例

```python
# 业务代码 — 在任何profile下完全相同
from datamind import get_storage, get_compute

def run_quality_check(table_name: str, zone: str):
    storage = get_storage()      # ← profile驱动，返回LocalFS或S3Backend
    compute = get_compute()      # ← profile驱动，返回DuckDBEngine或SparkEngine

    path = f"{zone}/{table_name}"

    if not storage.exists(path):
        return {"status": "missing", "table": table_name}

    compute.register_table(table_name, path)

    result = compute.execute(f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT order_id) AS unique_keys
        FROM {table_name}
    """)

    return compute.collect(result)
```

---

## 4. 数据契约（剖面驱动）

### 4.1 契约层次

数据契约也按剖面分级——不是所有剖面都需要完整的契约生命周期：

```
dev:     契约 = YAML声明（Schema + 基础规则），开发者约定
staging: 契约 = YAML + 自动化Schema检查（CI/CD）
prod:    契约 = 完整生命周期（注册→评审→发布→消费→变更→废弃）
```

### 4.2 契约定义

```yaml
# config/data_contracts/detail/order_detail.yaml
contract:
  name: order_detail
  zone: detail
  min_profile: staging      # ← 在哪个profile开始生效

  schema:
    columns:
      - name: order_id
        type: string
        nullable: false
      - name: amount
        type: decimal(12,2)
        nullable: false
      - name: order_time
        type: timestamp
        nullable: false

  quality:
    rules:
      - name: "主键非空"
        dimension: completeness
        sql: "SELECT COUNT(*) FROM {table} WHERE order_id IS NULL"
        expectation: "= 0"
        severity:
          dev: warn          # ← dev剖面下只告警
          staging: warn      # ← staging剖面下也只告警
          prod: block        # ← prod剖面下阻塞写入
```

**同一个规则，按剖面改变执行模式。**

### 4.3 契约检查如何融入ETL

```python
# dbt的post-hook — 在dbt层面统一触发，不侵入SQL
# dbt_project.yml
models:
  +post-hook:
    - "{{ check_contract(this, target.profile_name) }}"

# macros/check_contract.sql
{% macro check_contract(model, profile) %}
    {% set contract = load_contract(model.name) %}
    {% for rule in contract.quality.rules %}
        {% set result = run_query(rule.sql | replace('{table}', model)) %}
        {% if result[0][0] != 0 and rule.severity[profile] == 'block' %}
            {{ exceptions.raise_compiler_error("Contract violation: " + rule.name) }}
        {% elif result[0][0] != 0 and rule.severity[profile] == 'warn' %}
            {{ log("WARNING: " + rule.name, info=True) }}
        {% endif %}
    {% endfor %}
{% endmacro %}
```

---

## 5.1 数据采集/集成：IngestionInterface

数据采集是用户要求的4大核心能力之一。同样遵循接口-后端弹性模式：

```python
class IngestionInterface(ABC):
    @abstractmethod
    def ingest_batch(self, source_config: dict) -> str: ...
    @abstractmethod
    def ingest_stream(self, source_config: dict) -> str: ...
    @abstractmethod
    def list_sources(self) -> list[dict]: ...
    @abstractmethod
    def get_status(self, ingestion_id: str) -> dict: ...
```

### 采集后端矩阵

| profile | 批量采集 | 流式采集 | 说明 |
|---------|---------|---------|------|
| **dev** | Python脚本（pandas read_csv/read_json → Parquet） | 无 | 手动下载公开数据集，脚本转Parquet |
| **staging** | Python脚本 + MinIO上传 | 无 | 定时脚本拉取，存入MinIO |
| **prod** | Airbyte（配置化200+连接器） | Kafka + Debezium CDC | 生产级采集，支持CDC |
| **global** | 每区域Airbyte | 每区域Kafka + Debezium | 区域自治采集 |

### dev profile 采集实现

```python
# scripts/ingest_dev.py
class DevIngestion(IngestionInterface):
    def ingest_batch(self, source_config: dict) -> str:
        if source_config["type"] == "csv":
            df = pd.read_csv(source_config["url"])
        elif source_config["type"] == "parquet":
            df = pd.read_parquet(source_config["url"])
        elif source_config["type"] == "api":
            df = pd.DataFrame(requests.get(source_config["url"]).json())

        df["_ingested_at"] = datetime.now()
        df["_source"] = source_config["name"]

        output_path = f"data/raw/{source_config['name']}.parquet"
        df.to_parquet(output_path)
        return output_path
```

### prod profile 采集实现

```yaml
# config/ingestion/orders_source.yaml (Airbyte配置)
source:
  type: postgres
  config:
    host: ${DB_HOST}
    port: 5432
    database: production
    schema: public
    tables: ["orders", "payments", "customers"]

destination:
  type: s3
  config:
    bucket: datamind-prod
    path_prefix: raw/
    format: parquet

schedule: "0 */6 * * *"   # 每6小时全量同步
```

### 采集配置统一

所有profile共用同一份采集源定义，差异在执行方式：

```yaml
# config/sources.yaml — 所有profile共用
sources:
  - name: orders
    type: csv                    # dev: 直接读CSV
    url: "https://example.com/orders.csv"
    # prod覆盖:
    # type: postgres
    # host: ${DB_HOST}
    schedule: "0 */6 * * *"

  - name: user_behavior
    type: api
    url: "https://api.example.com/behavior"
    schedule: "0 2 * * *"
```

```yaml
# config/profile.yaml 中的采集配置
ingestion:
  backend: script               # dev=script, staging=script+minio, prod=airbyte
  stream_backend: none          # dev=none, prod=kafka
```

---

## 5.2 SQL兼容性保证

### 5.1 兼容子集策略

业务SQL使用DuckDB和Spark的**交集**语法，方言功能通过dbt宏适配：

```sql
-- ✅ 兼容语法（DuckDB和Spark都支持）
SELECT
    DATE_TRUNC('month', order_time) AS order_month,
    SUM(amount) AS total_amount,
    COUNT(DISTINCT user_id) AS user_count
FROM {{ ref('stg_orders') }}
WHERE order_status = 'completed'
GROUP BY 1

-- ⚠️ 方言差异通过宏适配
-- DuckDB:     CURRENT_DATE - INTERVAL '30' DAY
-- Spark SQL:  DATE_SUB(CURRENT_DATE(), 30)
-- 用宏统一：
WHERE order_time >= {{ date_sub('CURRENT_DATE', 30) }}
```

### 5.2 dbt宏适配

```sql
-- macros/cross_dialect.sql

{% macro date_sub(date_expr, days) %}
    {% if target.type == 'duckdb' %}
        {{ date_expr }} - INTERVAL '{{ days }}' DAY
    {% elif target.type == 'spark' %}
        DATE_SUB({{ date_expr }}, {{ days }})
    {% endif %}
{% endmacro %}

{% macro current_timestamp() %}
    {% if target.type == 'duckdb' %}
        CURRENT_TIMESTAMP
    {% elif target.type == 'spark' %}
        CURRENT_TIMESTAMP()
    {% endif %}
{% endmacro %}
```

这样，同一份SQL在不同后端都能运行。

---

## 6. 数据流转示例

以"电商日度营收汇总"为例，展示同一份ETL代码在不同剖面下的行为：

### 6.1 dev剖面

```
Raw: data/raw/orders.parquet → DuckDB读入
     ↓ (dbt staging: 简单格式化)
Cleaned: data/cleaned/stg_orders.parquet → 类型转换+空值填充
     ↓ (dbt intermediate: 直通)
Detail: data/detail/int_order_detail.parquet → SELECT * FROM stg_orders (1:1映射)
     ↓ (dbt marts: 简单聚合)
Summary: data/summary/fct_daily_revenue.parquet → GROUP BY date, SUM(amount)
     ↓ (dbt marts: 主题宽表)
App: data/app/app_daily_revenue.parquet → 面向业务的最终表
```

### 6.2 prod剖面

```
Raw: s3://datamind/raw/orders.parquet → 通过StorageInterface读取
     ↓ (dbt staging: 完整清洗)
Cleaned: s3://datamind/cleaned/stg_orders (Iceberg表) → 编码统一+异常值处理
     ↓ (dbt intermediate: 完整关联)
Detail: s3://datamind/detail/int_order_detail (Iceberg表) → 维度JOIN+业务解码+去重
     ↓ (dbt marts: 口径统一聚合)
Summary: s3://datamind/summary/fct_daily_revenue (Iceberg表) → 多维度+同比环比
     ↓ (dbt marts: 主题宽表)
App: s3://datamind/app/app_daily_revenue (Iceberg表) → 面向业务的最终表
```

**关键**：两个profile下，marts模型中的 `ref('int_order_detail')` 完全一致。差异在 intermediate 模型内部：dev是直通，prod是完整关联。

---

## 7. 项目目录结构（弹性版）

```
datamind/
├── config/
│   └── profile.yaml              # ★ 唯一的切换点
│
├── dbt_project/                   # 业务逻辑层（所有profile共用）
│   ├── dbt_project.yml
│   ├── profiles/                  # 各profile的dbt连接配置
│   │   ├── dev.yml                # DuckDB + 本地路径
│   │   ├── staging.yml            # DuckDB + MinIO路径
│   │   └── prod.yml               # Spark + S3路径
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/          # prod profile启用
│   │   └── marts/
│   ├── macros/
│   │   └── cross_dialect.sql      # SQL方言适配
│   └── tests/
│
├── datamind/                      # Python包
│   ├── interfaces/                # 抽象接口（Layer 1）
│   │   ├── storage.py             # StorageInterface
│   │   ├── compute.py             # ComputeInterface
│   │   ├── message.py             # MessageInterface
│   │   ├── scheduler.py           # SchedulerInterface
│   │   └── metadata.py            # MetadataInterface
│   ├── backends/                  # 可插拔后端（Layer 0）
│   │   ├── storage/
│   │   │   ├── local_fs.py        # dev
│   │   │   ├── minio_fs.py        # staging
│   │   │   └── s3_fs.py           # prod/global
│   │   ├── compute/
│   │   │   ├── duckdb_engine.py   # dev/staging
│   │   │   └── spark_engine.py    # prod/global
│   │   └── ...
│   ├── core/
│   │   └── factory.py             # get_storage(), get_compute() 等工厂函数
│   └── __init__.py
│
├── api/                           # API服务
├── dashboard/                     # Streamlit仪表盘
├── screen/                        # 实时大屏
├── scripts/
│   ├── setup.sh
│   └── demo.sh
├── Makefile
└── docker-compose.yml
```