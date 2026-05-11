# DataMind 平台工程

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v1.0 | 2026-05-11 | DataMind Team | 初始版本 |
| v3.0 | 2026-05-11 | DataMind Team | 重写为弹性框架：profile驱动的平台工程 |

---

## 1. 设计理念：平台工程也是弹性的

数据平台是一个**内部产品**，有两类用户：

- **数据工程师**（开发者）— 构建数据管线、维护数据资产
- **业务人员**（终端用户）— 消费数据、做业务决策

平台工程的核心目标不随profile改变，但**实现方式随profile升级**：

| 用户 | 目标 | dev profile | prod profile |
|------|------|-------------|-------------|
| 数据工程师 | 10分钟上手 | `make dev` 一键启动 | CI/CD + 代码评审 |
| 业务人员 | 3秒取数 | 模板匹配查询 | LLM自然语言查询 |

**弹性原则**：平台工程组件也通过接口-后端模式实现弹性切换。

```python
class SchedulerInterface:
    def schedule(self, pipeline: dict) -> str: ...
    def trigger(self, pipeline_id: str) -> str: ...
    def status(self, run_id: str) -> dict: ...
    def backfill(self, pipeline_id: str, start: date, end: date) -> list[str]: ...

class ObservabilityInterface:
    def log(self, level: str, message: str, context: dict): ...
    def metric(self, name: str, value: float, tags: dict): ...
    def trace(self, span_name: str, parent_id: str = None) -> str: ...
    def alert(self, severity: str, title: str, detail: str): ...
```

---

## 2. 调度与编排：profile驱动的弹性

### 2.1 调度器后端矩阵

| profile | 调度后端 | 触发方式 | 特点 |
|---------|---------|---------|------|
| **dev** | APScheduler（Python进程内） | 时间 + 手动触发 | 零系统依赖，跨平台（Windows/macOS/Linux） |
| **staging** | Dagster（单实例） | 时间 + 手动触发 | 可视化DAG、重跑、回填 |
| **prod** | Dagster（集群） + Kafka | 时间 + 事件 + 手动 | 高可用、流批一体、SLA管理 |
| **global** | Dagster（多区域） + Kafka（多集群） | 时间 + 事件 + 跨区域 | 区域自治、全局协调 |

### 2.2 接口抽象

```python
# src/scheduler/interface.py
from abc import ABC, abstractmethod
from datetime import date

class SchedulerInterface(ABC):
    @abstractmethod
    def schedule(self, pipeline_def: dict) -> str: ...
    @abstractmethod
    def trigger(self, pipeline_id: str, params: dict = None) -> str: ...
    @abstractmethod
    def status(self, run_id: str) -> dict: ...
    @abstractmethod
    def backfill(self, pipeline_id: str, start: date, end: date) -> list[str]: ...

# src/scheduler/apscheduler_backend.py  (dev profile, 跨平台)
class APSchedulerBackend(SchedulerInterface):
    def __init__(self):
        from apscheduler.schedulers.background import BackgroundScheduler
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()

    def schedule(self, pipeline_def: dict) -> str:
        cron_expr = pipeline_def.get("cron", "0 2 * * *")
        job_id = f"pipeline_{pipeline_def['model']}"
        self._scheduler.add_job(
            self._run_dbt,
            'cron',
            **self._parse_cron(cron_expr),
            id=job_id,
            args=[pipeline_def['model']]
        )
        return job_id

    def trigger(self, pipeline_id: str, params: dict = None) -> str:
        job = self._scheduler.get_job(pipeline_id)
        if job:
            job.modify(next_run_time=datetime.now())
        return pipeline_id

    @staticmethod
    def _run_dbt(model: str):
        import subprocess
        subprocess.run(["dbt", "run", "--select", model], check=True)
```

```python
# src/scheduler/dagster_backend.py  (staging/prod profile)
class DagsterScheduler(SchedulerInterface):
    def schedule(self, pipeline_def: dict) -> str:
        from dagster import ScheduleDefinition, job, op
        # 动态构建 Dagster Job
        job_def = self._build_dagster_job(pipeline_def)
        schedule = ScheduleDefinition(job=job_def, cron_schedule=pipeline_def["cron"])
        return schedule
```

### 2.3 Profile切换示例

```yaml
# config/profile.yaml
profile: dev
scheduler:
  backend: apscheduler        # dev → apscheduler, staging/prod → dagster
```

切换profile后，所有ETL任务的调度后端自动切换，**业务代码（dbt SQL）不变**。

### 2.4 调度能力对比

| 能力 | dev (APScheduler) | staging (Dagster单机) | prod (Dagster集群) |
|------|-------------------|---------------------|-------------------|
| 定时触发 | ✅ | ✅ | ✅ |
| 依赖编排 | ❌ (需手动排序) | ✅ DAG | ✅ DAG |
| 可视化 | ❌ | ✅ Dagit UI | ✅ Dagit UI |
| 回填 | ❌ | ✅ 一键回填 | ✅ 一键回填 |
| 事件触发 | ❌ | ❌ | ✅ Kafka触发 |
| 失败重试 | ❌ | ✅ 自动重试 | ✅ 自动重试+指数退避 |
| SLA管理 | ❌ | ❌ | ✅ SLA监控 |
| 资源隔离 | ❌ 单进程 | ❌ 单实例 | ✅ 按Job分配资源 |
| 跨平台 | ✅ Windows/macOS/Linux | ✅ | ✅ |

---

## 3. 开发者体验（DX）

### 3.1 开发者工作流（所有profile通用，实现不同）

```
发现数据 ──→ 开发管线 ──→ 测试验证 ──→ 发布上线 ──→ 监控运维

  dev:     本地文件浏览   dbt本地运行    dbt test     手动运行      日志查看
  staging: OpenMetadata   dbt + Dagster  CI自动测试   GitHub Actions Dagster UI
  prod:    OpenMetadata   dbt + Dagster  质量门禁     CI/CD审批     Prometheus
```

### 3.2 本地开发环境（dev profile）

```bash
# 一键启动（dev profile）
make dev

# 自动完成：
# 1. Python虚拟环境 + 依赖安装
# 2. 下载Olist数据集到 data/raw/
# 3. 启动DuckDB（本地文件模式）
# 4. 启动FastAPI（热重载）
# 5. 启动Streamlit（热重载）
# 6. 注册APScheduler定时任务

# 开发ETL
cd dbt_project
dbt run --target dev
dbt test --target dev

# 预览数据
make query SQL="SELECT * FROM fct_daily_revenue LIMIT 10"
```

### 3.3 CI/CD管线（staging + prod profile）

```yaml
# .github/workflows/data-pipeline.yml
name: Data Pipeline CI/CD

on:
  pull_request:
    paths: ['dbt_project/**', 'scripts/**']

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        profile: [dev, staging]  # 多profile并行测试

    steps:
      - uses: actions/checkout@v4

      - name: Setup
        run: pip install -r requirements.txt

      - name: dbt compile check
        run: cd dbt_project && dbt compile --target ${{ matrix.profile }}

      - name: dbt test
        run: cd dbt_project && dbt test --target ${{ matrix.profile }}

      - name: Contract validation
        run: python scripts/validate_contracts.py --profile ${{ matrix.profile }}

      - name: Quality gate
        run: python scripts/quality_gate.py --profile ${{ matrix.profile }}

  deploy-staging:
    needs: test
    if: github.ref == 'refs/heads/develop'
    steps:
      - name: Deploy to staging
        run: python scripts/deploy.py --profile staging

  deploy-prod:
    needs: test
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Deploy to production
        run: python scripts/deploy.py --profile prod
```

**关键**：CI/CD中同时运行 `dev` 和 `staging` 两个profile的测试，确保代码在两个profile下都能通过。Merge到 `develop` → 自动部署staging，Merge到 `main` → 需审批部署prod。

---

## 4. 数据API（弹性设计）

### 4.1 API定位：批量数据服务优先

数据平台的API首要服务的是**大批量数据流**，不是单次小查询。

| API类型 | 优先级 | 典型场景 | 数据量 |
|---------|--------|---------|--------|
| 批量导入 | 🔴 最高 | 每日数据采集入库 | 百万~十亿行 |
| 批量导出 | 🔴 最高 | ML训练数据导出、报表数据导出 | 百万~十亿行 |
| 批量同步 | 🟡 高 | 下游系统数据同步 | 万~百万行 |
| 流式订阅 | 🟡 高 | 实时应用数据消费 | 万行/秒 |
| 交互查询 | 🟢 中 | 分析师取数 | 千~万行 |

### 4.2 API端点（所有profile一致）

**批量数据流API（核心）**：

```
POST /api/v1/ingest/batch
{
  "source": "orders",
  "format": "csv",
  "options": {"delimiter": ",", "encoding": "utf-8"}
}
→ 返回: {"ingestion_id": "ing_123", "status": "running"}

POST /api/v1/export/batch
{
  "source": "app/app_daily_revenue",
  "format": "parquet",
  "target": "file",
  "target_path": "ml/feature_store/orders",
  "filters": [{"field": "order_month", "op": ">=", "value": "2026-01"}]
}
→ 返回: {"export_id": "exp_456", "status": "running", "rows": 1500000}

GET /api/v1/export/{export_id}/status
→ 返回: {"status": "completed", "rows_exported": 1500000, "size_mb": 234}

POST /api/v1/sync
{
  "source": "detail/int_order_detail",
  "target": {"type": "api", "url": "https://downstream.example.com/data"},
  "mode": "incremental",
  "watermark": "2026-05-10T00:00:00Z"
}
→ 返回: {"sync_id": "syn_789", "status": "running"}
```

**流式数据API（prod+ profile）**：

```
GET /api/v1/stream/{topic}
  ?start_from=latest
  → SSE/WebSocket: 实时数据流推送

POST /api/v1/stream/subscribe
{
  "topic": "orders.detail",
  "consumer_group": "ml_pipeline",
  "auto_offset_reset": "latest"
}
→ 返回: {"subscription_id": "sub_abc", "status": "active"}
```

**交互查询API（辅助）**：

```
POST /api/v1/query
{
  "dataset": "fct_daily_revenue",
  "dimensions": ["region"],
  "metrics": ["net_revenue", "order_count"],
  "filters": [{"field": "month", "op": ">=", "value": "2026-01"}],
  "limit": 100
}

POST /api/v1/query/natural
{
  "question": "上个月各地区的销售额对比"
}

GET /api/v1/catalog/search?q=revenue
GET /api/v1/lineage/{dataset}/downstream?depth=3
GET /api/v1/quality/{dataset}/score
```

### 4.3 API层接口抽象

数据API通过 `QueryInterface` 实现profile适配：

```python
class QueryInterface(ABC):
    @abstractmethod
    def execute(self, sql: str, params: dict = None) -> dict: ...
    @abstractmethod
    def natural_query(self, question: str, context: dict = None) -> dict: ...
    @abstractmethod
    def catalog(self, query: str = None) -> list[dict]: ...
```

| profile | Compute Backend | Query Backend | API部署 | Natural Query |
|---------|----------------|--------------|---------|--------------|
| dev | DuckDB本地 | DuckDB本地 | FastAPI单进程 | 模板匹配 |
| staging | DuckDB（MinIO数据） | DuckDB（MinIO数据） | FastAPI + Docker | 模板 + LLM |
| prod | Spark | Trino / ClickHouse | FastAPI + K8s | LLM + Agent |
| global | 区域Spark | 区域Trino + ClickHouse | FastAPI + CDN + 多区域 | LLM + RAG |

### 4.2 API端点（所有profile一致）

```
POST /api/v1/query
{
  "dataset": "fct_daily_revenue",
  "dimensions": ["region"],
  "metrics": ["net_revenue", "order_count"],
  "filters": [{"field": "month", "op": ">=", "value": "2026-01"}],
  "limit": 100
}

POST /api/v1/query/natural
{
  "question": "上个月各地区的销售额对比"
}

GET /api/v1/catalog/search?q=revenue
GET /api/v1/lineage/{dataset}/downstream?depth=3
GET /api/v1/quality/{dataset}/score
```

### 4.3 缓存策略（profile驱动）

| profile | L1缓存 | L2缓存 | 适用场景 |
|---------|--------|--------|---------|
| dev | 进程内存 (TTL=5min) | 无 | 单人使用，不需要分布式缓存 |
| staging | 进程内存 (TTL=1min) | Redis (TTL=10min) | 团队使用，减少重复计算 |
| prod | 进程内存 (TTL=30s) | Redis Cluster (TTL=5min) | 高并发，多层缓存保证性能 |

### 4.4 限流防护

| 防护措施 | dev | staging | prod |
|---------|-----|---------|------|
| 查询超时 | 60秒 | 30秒 | 15秒 |
| 并发限制 | 无 | 10/用户 | 20/用户 |
| 结果集限制 | 无 | 10万行 | 50万行 |
| 请求频率 | 无 | 60次/分钟 | 120次/分钟 |

**dev profile 宽松是为了开发调试方便；prod profile 严格是为了保护生产资源。**

---

## 5. 可观测性（profile驱动的弹性）

### 5.1 可观测性后端矩阵

| profile | 日志 | 指标 | 追踪 | 告警 |
|---------|------|------|------|------|
| **dev** | Python logging → stdout | 无 | 无 | 无 |
| **staging** | 结构化JSON日志 → 文件 | Prometheus → Grafana | OpenTelemetry → Jaeger | Grafana Alerting |
| **prod** | 结构化JSON日志 → ELK | Prometheus → Grafana | OpenTelemetry → Jaeger | PagerDuty + 分级 |
| **global** | ELK多集群聚合 | Thanos全局聚合 | 跨区域Trace关联 | PagerDuty + 跨区域值班 |

### 5.2 接口抽象

```python
class ObservabilityInterface(ABC):
    @abstractmethod
    def log(self, level: str, message: str, context: dict = None): ...
    @abstractmethod
    def metric(self, name: str, value: float, tags: dict = None): ...
    @abstractmethod
    def trace(self, span_name: str, parent_id: str = None) -> 'SpanContext': ...

# dev backend：所有方法no-op或print
class DevObservability(ObservabilityInterface):
    def log(self, level, message, context=None):
        print(f"[{level.upper()}] {message}")
    def metric(self, name, value, tags=None):
        pass  # dev不收集指标
    def trace(self, span_name, parent_id=None):
        return NoopSpan()
```

**业务代码调用 `obs.log("error", "ETL failed", {"pipeline": "daily_revenue"})` 在dev输出到stdout，在prod输出到ELK。代码零改动。**

### 5.3 关键监控指标

| 类别 | 指标 | prod告警阈值 | staging告警阈值 | dev |
|------|------|-------------|---------------|-----|
| 数据质量 | 质量门禁通过率 | <99.5% | <95% | 无告警 |
| 数据时效 | 数据新鲜度 | >SLA 1.5x | >SLA 3x | 无告警 |
| 管线健康 | ETL成功率 | <99% | <95% | 无告警 |
| API性能 | P99延迟 | >1秒 | >3秒 | 无告警 |
| API可用 | 成功率 | <99.9% | <99% | 无告警 |

---

## 6. 自助服务（profile驱动的能力渐进）

### 6.1 自助能力矩阵

| 角色 | 能力 | dev | staging | prod |
|------|------|-----|---------|------|
| 数据分析师 | SQL工作台 | 无（本地dbt） | Superset SQL Lab | Superset SQL Lab（生产数据） |
| 业务运营 | 仪表盘 | Streamlit（demo） | Superset Dashboard | Superset + 实时刷新 |
| 管理层 | 大屏 | Streamlit（demo） | Superset嵌入 | 自研大屏 + 实时推送 |

### 6.2 自助服务护栏

每个自助服务都有护栏，**严重程度随profile升级**：

| 护栏 | dev | staging | prod |
|------|-----|---------|------|
| 查询超时 | 无限制 | 60秒自动终止 | 30秒自动终止 |
| PII脱敏 | 无 | 自动脱敏(partial) | 自动脱敏(replace)+审批 |
| 数据导出 | 无限制 | 标记日志 | 审批 + 审计 |
| 成本显示 | 不显示 | 显示查询行数 | 显示估算成本 |

---

## 7. profile.yaml：平台工程配置项

```yaml
# config/profile.yaml — 完整平台工程配置
profile: dev

scheduler:
  backend: apscheduler       # dev=apscheduler, staging=dagster, prod=dagster_cluster

api:
  host: 0.0.0.0
  port: 8000
  workers: 1               # dev=1, staging=2, prod=4+
  cache_backend: memory    # dev=memory, staging=redis, prod=redis_cluster

observability:
  log_backend: stdout      # dev=stdout, staging=file, prod=elasticsearch
  metrics_backend: none    # dev=none, staging=prometheus, prod=prometheus
  trace_backend: none      # dev=none, staging=jaeger, prod=jaeger

ci_cd:
  auto_deploy: false       # dev=false, staging=true, prod=true (+ approval)

governance:
  quality_severity: warn   # dev=warn, staging=block_non_gold, prod=block_all
  contract_enforcement: warn