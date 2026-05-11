# DataMind Demo 实施方案 — dev 剖面

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v3.0 | 2026-05-11 | DataMind Team | 重新设计：作为弹性框架的dev剖面实例化 |

---

## 1. 定位

Demo不是独立的项目，而是弹性框架在 `dev` 剖面下的实例化。

```
同一套 datamind/ 代码
     │
     ├── profile: dev  → Demo (笔记本, $0)
     ├── profile: staging → 单机生产验证
     ├── profile: prod → 生产集群
     └── profile: global → 全球部署
```

**Demo成功 = dev剖面跑通了，证明框架设计正确，然后切到staging就是生产。**

---

## 2. 环境要求

| 项目 | 要求 |
|------|------|
| Python | 3.10+ |
| 内存 | 8GB |
| 磁盘 | 5GB |
| Docker | 仅需运行Superset（可选） |
| 云服务 | 无 |

---

## 3. 项目初始化

```bash
git clone <repo>
cd datamind

# 安装
pip install -r requirements.txt

# 确认profile
cat config/profile.yaml
# profile: dev    ← 当前是dev剖面

# 初始化数据
python scripts/setup_dev.py
# 下载Olist数据集 + 生成模拟数据 → data/raw/
```

---

## 4. 数据结构（dev剖面：5层统一，中间层直通）

```
data/
├── raw/                              # Raw Zone
│   ├── orders.parquet                # Olist订单数据
│   ├── payments.parquet              # Olist支付数据
│   ├── reviews.parquet               # Olist评价数据
│   ├── products.parquet              # Olist商品数据
│   ├── customers.parquet             # Olist客户数据
│   └── user_behavior.parquet         # 模拟用户行为
│
├── cleaned/                          # Cleaned Zone (staging models)
│   ├── stg_orders.parquet            # 简单格式化：类型转换+空值填充
│   ├── stg_payments.parquet
│   ├── stg_customers.parquet
│   └── stg_products.parquet
│
├── detail/                           # Detail Zone (intermediate models)
│   ├── int_order_detail.parquet      # dev: 直通(1:1) / prod: 完整关联
│   ├── int_payment_detail.parquet
│   └── int_customer_detail.parquet
│
├── summary/                          # Summary Zone
│   ├── fct_daily_revenue.parquet     # dev: 简单聚合 / prod: 口径统一
│   └── fct_monthly_kpi.parquet
│
└── app/                              # App Zone (marts)
    ├── app_daily_revenue.parquet     # 日度营收（面向业务）
    ├── app_customer_segments.parquet # 客户分群
    └── app_product_performance.parquet
```

**说明**：dev剖面下所有5层都存在，但 detail 和 summary 层使用直通/简单模式。这保证了所有profile的 `ref()` 链完全一致——marts 永远引用 `ref('int_order_detail')`，不需要按profile改写SQL。

---

## 5. 三杀演示

### 5.1 实时大屏

**实现**：ECharts HTML + Python数据模拟器

```python
# scripts/simulate_realtime.py
# 用 profile: dev 下的 DuckDB 查询聚合数据，模拟实时订单流入

from datamind import get_storage, get_compute

storage = get_storage()    # dev: LocalFS
compute = get_compute()    # dev: DuckDB

# 读取历史数据的分布特征
daily_stats = compute.execute("""
    SELECT
        DATE_TRUNC('day', order_time) as d,
        COUNT(*) as cnt,
        AVG(total_amount) as avg_amount
    FROM app_daily_revenue
    GROUP BY 1 ORDER BY 1
""").collect()

# 按分布随机生成新订单，推送给前端
```

**启动**：`python screen/server.py` → http://localhost:3000

### 5.2 自然语言取数

**dev剖面实现**：模板匹配（零LLM成本）

```python
# api/services/text_to_sql_dev.py
# dev剖面下不使用LLM，用预定义模板匹配

QUERY_TEMPLATES = [
    {
        "patterns": ["销售", "营收", "收入", "revenue", "卖了"],
        "sql": """
            SELECT {time_dim}, SUM(net_revenue) AS revenue
            FROM app_daily_revenue
            WHERE 1=1 {time_filter} {extra_filter}
            GROUP BY {time_dim}
            ORDER BY {time_dim} DESC
        """,
        "dimensions": {"time_dim": "order_date"},
        "chart": "line"
    },
    {
        "patterns": ["订单量", "订单数", "有多少单", "orders"],
        "sql": """
            SELECT {time_dim}, SUM(order_count) AS orders
            FROM app_daily_revenue
            WHERE 1=1 {time_filter} {extra_filter}
            GROUP BY {time_dim}
            ORDER BY {time_dim} DESC
        """,
        "dimensions": {"time_dim": "order_date"},
        "chart": "bar"
    },
    {
        "patterns": ["满意度", "评分", "评价", "rating"],
        "sql": """
            SELECT product_category, AVG(review_score) AS avg_rating
            FROM app_product_performance
            WHERE 1=1 {time_filter}
            GROUP BY product_category
            ORDER BY avg_rating DESC
        """,
        "chart": "radar"
    },
    {
        "patterns": ["品类", "分类", "category", "哪个"],
        "sql": """
            SELECT product_category, SUM(net_revenue) AS revenue
            FROM app_product_performance
            WHERE 1=1 {time_filter}
            GROUP BY product_category
            ORDER BY revenue DESC
            LIMIT 10
        """,
        "chart": "horizontal_bar"
    },
    {
        "patterns": ["客户", "用户", "customer", "user"],
        "sql": """
            SELECT customer_state, COUNT(DISTINCT customer_id) AS customers
            FROM app_customer_segments
            GROUP BY customer_state
            ORDER BY customers DESC
        """,
        "chart": "map"
    }
]
```

**切换剖面后**：profile切到staging，模板引擎替换为LLM引擎——同一接口，不同实现。

### 5.3 异常自动发现

**dev剖面实现**：统计方法（零LLM成本）

```python
# api/services/anomaly_detector_dev.py

class StatisticalDetector:
    def detect(self, dataset: str, metric: str, window: int = 30):
        # 从DuckDB拉取历史数据
        data = self.compute.execute(f"""
            SELECT {metric} AS value, order_date
            FROM {dataset}
            ORDER BY order_date DESC LIMIT {window}
        """).collect()

        values = [r['value'] for r in data]

        # 3σ检测
        mean = sum(values) / len(values)
        std = (sum((v - mean)**2 for v in values) / len(values)) ** 0.5
        threshold = 3 * std

        latest = values[0]
        if abs(latest - mean) > threshold:
            # 根因追踪：通过血缘反向查找上游异常
            root_cause = self.trace_root_cause(dataset, metric)
            return {
                "severity": "critical",
                "message": f"{dataset}.{metric} 异常偏离 {abs(latest-mean)/mean*100:.1f}%",
                "root_cause": root_cause
            }
        return None

    def trace_root_cause(self, dataset: str, metric: str) -> list:
        # 从血缘数据库查上游
        upstream = self.metadata.lineage(dataset)
        causes = []
        for up in upstream:
            # 递归检查上游是否有异常
            anomaly = self.detect(up.table, up.column)
            if anomaly:
                causes.append({
                    "dataset": up.table,
                    "metric": up.column,
                    "issue": anomaly
                })
        return causes
```

---

## 6. 一键命令

```bash
# 初始化
make setup-dev       # 下载数据 + 初始化元数据

# 运行ETL（dev profile）
make etl             # dbt run --profile dev

# 启动所有服务
make up-dev          # 启动 FastAPI + Streamlit + 大屏

# 打开演示
make demo            # 打开浏览器

# 切换剖面验证
DATAMIND_PROFILE=staging make etl     # 在staging剖面运行同一套dbt代码
```

---

## 7. 演示流程（5分钟）

Demo的核心不是"3秒取数"，而是**大批量数据全流程**——采集→加工→分发。

| 时间 | 内容 | 操作 | 展示的核心价值 |
|------|------|------|---------------|
| 0:00-1:00 | 批量数据采集 | `make ingest` → 10万条数据5秒入库 | 采集吞吐量 |
| 1:00-2:30 | 批量ETL加工 | `make etl` → 5层加工全链路完成 | 加工能力 |
| 2:30-3:30 | 批量数据导出 | `make export` → 导出Parquet给ML训练 + CSV给报表 | 分发能力 |
| 3:30-4:00 | 数据治理 | 展示质量规则 + 血缘 + 异常检测 | 治理贯穿 |
| 4:00-5:00 | **弹性证明** | `export DATAMIND_PROFILE=staging` → `make etl` → 同一套代码在staging剖面运行 | 弹性框架 |

**演示的核心叙事**：

```
"你看，10万条数据5秒就采集进来了，
 然后自动经过5层加工变成业务可用的数据，
 加工完的数据一键导出给ML训练和报表系统，
 整个过程有质量门禁和血缘追踪保证数据可信。

 而这一切，只需要改一行配置就能从笔记本迁移到集群。"
```

**杀手锏**：在领导面前现场切换profile，证明同一套代码确实能在不同规模运行。

---

## 8. 从Demo到生产的路径

```
dev (Demo)          staging               prod                global
───────             ────────              ────                ──────
笔记本, $0          单台服务器, $200/月     集群, $3K/月         多区域, $15K/月

      │                  │                    │                    │
      ▼                  ▼                    ▼                    ▼
  切换profile        切换profile           切换profile          切换profile
  = 0行代码改动      = 0行代码改动         = 0行代码改动        = 0行代码改动
```

每次切换只需要：
1. 修改 `config/profile.yaml` 中 `profile` 字段
2. 确保目标profile的后端已部署（如MinIO实例、Spark集群）
3. 运行 `make etl` 验证