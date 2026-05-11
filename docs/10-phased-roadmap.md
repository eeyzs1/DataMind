# DataMind 剖面升级路线图

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v3.0 | 2026-05-11 | DataMind Team | 重新设计：以剖面升级替代传统阶段划分 |

---

## 1. 升级路径

不是"Phase 1→2→3"的计划，而是**同一套代码在越来越大的基础设施上运行**：

```
dev            →   staging      →    prod        →    global
─────              ───────          ──────            ──────
笔记本               单台服务器        集群               多区域
2人, $0            2-3人, $200      5-8人, $3K        10人+, $15K
4周                 2周              2-3月             6-12月
功能完整             数据治理         业务模型           全球合规
```

### 1.1 dev → staging：从Demo到生产最小化

| 变更 | 说明 |
|------|------|
| 修改 `config/profile.yaml` | `profile: staging` |
| 部署 MinIO | Docker单节点，S3兼容 |
| 部署 PostgreSQL | Docker单节点 |
| 部署 Dagster | Docker单节点 |
| 部署 FastAPI | 生产配置(gunicorn/uvicorn) |
| **业务代码改动** | **0** |

### 1.2 staging → prod：从单机到分布式

| 变更 | 说明 |
|------|------|
| 修改 `config/profile.yaml` | `profile: prod` |
| 存储切到 S3 或 MinIO 集群 | StorageInterface自动切换 |
| 部署 Spark 集群 | 3节点起步 |
| 部署 Kafka | 3节点起步 |
| 部署 OpenMetadata | 替代自研元数据服务 |
| 激活质量门禁(block) | 同一份YAML，severity生效 |
| **业务代码改动** | **0** |

### 1.3 prod → global：从单区域到全球

| 变更 | 说明 |
|------|------|
| 修改 `config/profile.yaml` | `profile: global` |
| 每个区域部署一套 prod 基础设施 | 3个区域 |
| 部署全局控制平面 | 元数据同步 + 权限统一 |
| 配置数据驻留规则 | PII数据不出域 |
| 配置跨区域审批流 | GDPR合规 |
| **业务代码改动** | **0** |

---

## 2. 里程碑

### 2.1 dev 剖面（4周）

| 周 | 关键产出 |
|----|---------|
| W1 | 框架骨架：接口定义 + dev后端实现 + 数据初始化 |
| W2 | ETL管线：dbt staging + marts，3层数据流动 |
| W3 | 三杀特性：大屏 + 模板取数 + 异常检测 |
| W4 | 演示打磨：5分钟剧本 + 弹性切换证明 |

### 2.2 staging 剖面（2周）

| 周 | 关键产出 |
|----|---------|
| W1 | 基础设施：MinIO + PostgreSQL + Dagster 部署 |
| W2 | 治理激活：元数据目录 + CI/CD契约检查 + 数据血缘 |

### 2.3 prod 剖面（2-3月）

| 月 | 关键产出 |
|----|---------|
| M1 | 分布式基础设施：Spark + Kafka + S3 |
| M2 | 治理完善：OpenMetadata + 质量门禁(block) + 列级脱敏 |
| M3 | 业务模型：LightGBM销量预测 + XGBoost流失预测 |

### 2.4 global 剖面（6-12月）

| 阶段 | 关键产出 |
|------|---------|
| 区域部署 | 3个区域 × prod基础设施 |
| 全局治理 | 跨区域血缘 + 统一权限 + 数据驻留 |
| 合规 | GDPR + CCPA + 个保法 |
| ML平台 | 特征存储 + 在线推理 + 自动重训练 |

---

## 3. 人力需求

| 剖面 | 核心角色 | 人数 |
|------|---------|------|
| dev | 全栈数据工程师 | 2 |
| staging | 数据工程师 + DevOps | 2-3 |
| prod | 数据工程师×3 + 后端×1 + DevOps×0.5 + 治理×1 + 产品×0.5 | 5-8 |
| global | 上述 + 安全×1 + FE×1 | 10+ |

---

## 4. 决策检查点

每个剖面升级前需通过检查，失败则停留在当前剖面：

| 检查点 | 通过标准 |
|--------|---------|
| dev → staging | Demo获决策者认可；核心ETL稳定；接口实现无硬编码 |
| staging → prod | 数据量超单机能力(>500GB查询)；或并发超10；治理到位 |
| prod → global | 业务需求明确；合规评估通过；多区域基础设施预算到位 |

---

## 5. 风险与缓解

| 风险 | 缓解 |
|------|------|
| dev剖面演示失败 | 持续迭代；模板取数兜底；大屏效果优先 |
| staging→prod接口泄漏 | 代码审查强制检查：不允许`import boto3`/`import duckdb`出现在业务代码中 |
| SQL方言不兼容 | dbt宏覆盖差异；CI/CD在DuckDB和Spark两个后端上运行同一套测试 |
| 团队学习曲线 | dev剖面就是学习过程；dbt和DuckDB学习成本最低 |
| intermediate层条件逻辑维护复杂 | 限制条件逻辑只在intermediate层；marts层保持纯净 |

---

## 6. 跨Profile测试策略

### 6.1 测试金字塔

```
                    ┌──────────┐
                    │ E2E测试   │  每个profile跑一遍完整Demo流程
                   ┌┴──────────┴┐
                   │ 集成测试    │  dbt run + dbt test 在DuckDB和Spark两个后端
                  ┌┴────────────┴┐
                  │ 接口契约测试  │  每个Interface的每个后端实现都通过同一套测试
                 ┌┴──────────────┴┐
                 │ 单元测试        │  Python函数级测试，不依赖profile
                ┌┴────────────────┴┐
                │ 接口泄漏检查      │  业务代码不允许直接import后端库
                └──────────────────┘
```

### 6.2 接口泄漏检查（CI强制）

```bash
# scripts/check_interface_leak.sh
# 在CI中运行，确保业务代码不直接依赖后端实现

# 禁止在业务代码中出现后端库的直接导入
grep -rn "import duckdb\|import boto3\|from pyspark\|import minio\|from kafka" \
  --include="*.py" \
  --exclude-dir=backends \
  --exclude-dir=tests \
  datamind/ api/ scripts/

if [ $? -eq 0 ]; then
    echo "❌ 接口泄漏：业务代码直接导入了后端库！"
    exit 1
fi
echo "✅ 接口检查通过"
```

### 6.3 跨后端集成测试

```yaml
# .github/workflows/cross-profile-test.yml
name: Cross-Profile Test

on: [pull_request]

jobs:
  test-dev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements-dev.txt
      - run: cd dbt_project && dbt run --target dev
      - run: cd dbt_project && dbt test --target dev

  test-spark:
    runs-on: ubuntu-latest
    services:
      spark:
        image: bitnami/spark:latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements-spark.txt
      - run: cd dbt_project && dbt run --target prod
      - run: cd dbt_project && dbt test --target prod

  interface-contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/interfaces/ -v
      - run: bash scripts/check_interface_leak.sh
```

### 6.4 接口契约测试

```python
# tests/interfaces/test_storage_interface.py
import pytest
from datamind.interfaces.storage import StorageInterface

# 每个后端实现都必须通过同一套测试
@pytest.fixture(params=["local_fs", "minio", "s3"])
def storage(request):
    return create_storage_backend(request.param)

class TestStorageContract:
    def test_write_and_read(self, storage):
        df = pd.DataFrame({"a": [1, 2, 3]})
        storage.write_parquet(df, "test/table")
        result = storage.read_parquet("test/table")
        assert len(result) == 3

    def test_exists(self, storage):
        assert not storage.exists("test/nonexistent")
        storage.write_parquet(pd.DataFrame(), "test/empty")
        assert storage.exists("test/empty")

    def test_list_tables(self, storage):
        storage.write_parquet(pd.DataFrame({"x": [1]}), "test/t1")
        tables = storage.list_tables("test")
        assert "t1" in tables
```

### 6.5 Profile升级验证检查清单

每次profile升级前，必须通过以下自动化验证：

| 检查项 | 自动化方式 | 失败处理 |
|--------|-----------|---------|
| 所有dbt模型在目标profile编译通过 | `dbt compile --target <profile>` | 修复SQL兼容性 |
| 所有dbt测试在目标profile通过 | `dbt test --target <profile>` | 修复数据问题 |
| 接口泄漏检查通过 | `check_interface_leak.sh` | 移除直接导入 |
| 接口契约测试通过 | `pytest tests/interfaces/` | 修复后端实现 |
| E2E Demo在目标profile可运行 | `make demo PROFILE=<profile>` | 修复集成问题 |