# DataMind AI 融合架构

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v1.0 | 2026-05-11 | DataMind Team | 初始版本 |
| v2.0 | 2026-05-11 | DataMind Team | 重新设计：区分数据平面与控制平面，LLM不碰数据行 |
| v2.1 | 2026-05-11 | DataMind Team | 融入弹性框架：AI能力随profile渐进激活 |

---

## 0. AI能力与弹性框架

### 0.1 Profile驱动的AI能力渐进

AI能力也遵循弹性框架的设计原则——同一套代码，不同profile下激活不同级别的AI能力：

```
dev profile         staging profile       prod profile          global profile
───────────        ───────────────       ─────────────         ──────────────
零LLM              基础LLM交互            完整AI栈               AI闭环
模板匹配取数        LLM Text-to-SQL       LLM + Agent           RAG + 多语言
统计方法异常检测    LLM异常解释           传统ML模型             全局Feature Store
正则PII识别        元数据LLM补全         Feature Store          自动重训练
                  传统ML训练             全链路MLOps             跨区域模型

        升级路径：只改 config/profile.yaml 中 ai 配置块
        业务代码、dbt模型、数据质量规则完全不变
```

### 0.2 Profile-AI映射表

| AI能力 | dev | staging | prod | global |
|--------|-----|---------|------|--------|
| 智能取数 | 模板匹配（$0） | LLM Text-to-SQL | LLM + Agent | LLM + RAG |
| 异常检测 | 3σ/IQR统计方法 | 3σ/IQR统计方法 | 统计方法 + Isolation Forest | 统计方法 + 深度学习 |
| 异常解释 | 无 | LLM生成解释 | LLM + 上下文增强 | LLM + 多语言 |
| 质量检查 | SQL规则 | SQL规则 | SQL规则 + 统计校验 | SQL规则 + 跨区域校验 |
| PII识别 | 正则表达式 | 正则 + NER | 正则 + NER + 分类模型 | 多语言NER |
| 元数据补全 | 手动 | LLM生成描述 | LLM + 自动分类 | LLM + 多语言 |
| 业务预测 | 无 | LightGBM（离线） | LightGBM + Feature Store | LightGBM + 在线推理 |
| MLOps | 无 | 手动训练 | MLflow + 统计监控 | MLflow + 自动重训练 |

### 0.3 profile.yaml AI配置

```yaml
ai:
  control_plane:
    text_to_sql: template     # dev=template, staging=llm, prod=llm_agent, global=llm_rag
    anomaly_explanation: none # dev=none, staging=llm, prod=llm_context
    metadata_enrichment: none # dev=none, staging=llm, prod=llm
    code_generation: none     # dev=none, staging=llm, prod=llm

  data_plane:
    anomaly_detection: statistical  # dev=statistical, staging=statistical, prod=ml
    pii_detection: regex            # dev=regex, staging=regex_ner, prod=regex_ner_ml
    quality_check: sql_rules        # 所有profile一致（确定性方法）

  ml:
    training: false           # staging+: true
    feature_store: false      # prod+: true
    online_serving: false     # global: true
    auto_retraining: false    # global: true
```

---

## 1. 核心原则：两个平面，两种AI

### 1.1 问题本质

大数据平台的数据量是百万到亿级行。**LLM按Token计费、按秒响应，用它处理数据行是成本和效率的双重灾难。**

```
错误做法（成本和效率灾难）:
  100万行数据 → 逐行过LLM → 成本$5000+ / 延迟数小时 / 结果不可复现

正确做法:
  100万行数据 → SQL/规则/统计方法 → 成本$0 / 延迟秒级 / 结果确定性

  LLM只处理"人与平台之间的交互":
  用户提问 → 1次LLM调用 → 生成SQL → SQL处理100万行
  成本: 1次API调用 / 延迟: 1-3秒 / 结果: 确定性
```

### 1.2 两个平面

大数据平台存在两个本质不同的平面，AI在其中的角色完全不同：

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  控制平面 (Control Plane)                                            │
│  ─────────────────────────                                          │
│  · 数据量: 极少（用户输入、元数据、查询结果摘要）                       │
│  · 处理方式: LLM / Agent                                             │
│  · AI角色: 意图理解、代码生成、解释生成                                │
│  · 成本: 每次交互1次LLM调用，可承受                                    │
│  · 延迟: 1-5秒，用户可接受                                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    ↓ LLM生成SQL/规则/代码 ↓                  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  数据平面 (Data Plane)                                               │
│  ────────────────────                                               │
│  · 数据量: 百万/亿行                                                 │
│  · 处理方式: SQL / 规则引擎 / 统计方法 / 传统ML                       │
│  · AI角色: 不用LLM，用确定性方法                                      │
│  · 成本: $0（本地计算）                                               │
│  · 延迟: 毫秒到秒级                                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.3 AI技术选择矩阵

| 场景 | 数据量 | 正确选择 | 错误选择 | 理由 |
|------|--------|---------|---------|------|
| 数据质量检查 | 百万行 | SQL规则 + 统计方法 | ~~LLM逐行检查~~ | 成本差10000倍，效率差1000倍 |
| PII识别 | 百万行 | 正则 + 小型NER模型 | ~~LLM逐行扫描~~ | NER模型<10ms/行，LLM>1s/行 |
| 异常检测 | 百万行 | 3σ/IQR/Isolation Forest | ~~LLM判断~~ | 统计方法确定性、零成本 |
| 自然语言取数 | 1个问题 | LLM生成SQL | - | 1次调用，SQL处理大数据 |
| 元数据描述 | 几百个表 | LLM生成描述 | - | 几百次调用，总量可承受 |
| 异常解释 | 几个异常 | LLM生成解释 | - | 少量调用，价值高 |
| 销量预测 | 百万行 | LightGBM/Prophet | ~~LLM预测~~ | 传统ML确定性、可解释 |
| 推荐系统 | 百万用户 | 双塔/DeepFM | ~~LLM排序~~ | 传统ML毫秒级推理 |

### 1.4 设计原则

| 原则 | 含义 | 违反后果 |
|------|------|---------|
| **LLM不碰数据行** | LLM只处理用户交互和元数据，不处理数据行 | 成本爆炸、效率灾难 |
| **数据平面确定性** | 数据质量、异常检测等用确定性方法 | 结果不可复现、不可信 |
| **LLM是翻译器** | LLM把人的意图翻译成机器可执行的指令 | LLM变成处理器，架构混乱 |
| **传统ML处理规模** | 预测、分类、推荐用传统ML模型 | LLM推理成本和延迟不可接受 |
| **成本意识** | 每个AI调用都要评估成本/价值比 | 隐性成本失控 |

---

## 2. AI融合架构全景

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AI 融合架构 v2                                    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  控制平面: LLM处理人与平台的交互                                    │  │
│  │                                                                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │ 智能取数  │  │ 智能分析  │  │ 智能治理  │  │ 智能开发  │        │  │
│  │  │          │  │          │  │          │  │          │        │  │
│  │  │ 问题→SQL │  │ 异常→解释 │  │ 表→描述  │  │ 需求→代码 │        │  │
│  │  │ 1次LLM   │  │ 1次LLM   │  │ 1次LLM   │  │ 1次LLM   │        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  │       │              │              │              │              │  │
│  │       ▼              ▼              ▼              ▼              │  │
│  │  ┌─────────────────────────────────────────────────────────┐    │  │
│  │  │  LLM输出: SQL / 规则 / 代码 / 解释 / 描述                │    │  │
│  │  └─────────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                           │                                             │
│                           ▼                                             │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  数据平面: 确定性方法处理大数据                                     │  │
│  │                                                                   │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │ 质量检查  │  │ 异常检测  │  │ PII识别  │  │ 业务模型  │        │  │
│  │  │          │  │          │  │          │  │          │        │  │
│  │  │ SQL规则  │  │ 统计方法  │  │ 正则+NER │  │ 传统ML   │        │  │
│  │  │ 毫秒级   │  │ 毫秒级   │  │ 毫秒级   │  │ 毫秒级   │        │  │
│  │  │ $0      │  │ $0      │  │ $0      │  │ $0      │        │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 控制平面：LLM处理人与平台的交互

### 3.1 智能取数（Text-to-SQL）

**LLM的角色：翻译器 — 把自然语言翻译成SQL，SQL去处理大数据。**

```
用户: "上个月各地区的销售额对比"
     │
     ▼  ← LLM在这里：1次调用，~0.01美元，1-3秒
     │
生成SQL:
  SELECT region, SUM(net_revenue) AS revenue
  FROM fct_daily_revenue
  WHERE month = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1' MONTH)
  GROUP BY region
  ORDER BY revenue DESC
     │
     ▼  ← SQL执行：处理100万行，0.02秒，$0
     │
返回结果: 表格 + 图表
```

**成本分析**：

| 步骤 | 方法 | 数据量 | 成本 | 延迟 |
|------|------|--------|------|------|
| 意图→SQL | LLM | 1个问题 | ~$0.01 | 1-3秒 |
| SQL执行 | DuckDB | 100万行 | $0 | 0.02秒 |
| **总计** | | | **~$0.01** | **~3秒** |

对比错误做法：LLM直接处理100万行数据 → ~$5000，数小时。

#### 按profile渐进激活

| profile | 实现方式 | 准确率 | LLM成本/次 | 说明 |
|---------|---------|--------|-----------|------|
| dev | 模板匹配（预定义20+查询模板，零LLM调用） | ~80% | $0 | 用于Demo演示，零成本 |
| staging | LLM + Schema信息 + Few-shot | ~90% | ~$0.01 | 团队协作，按需LLM |
| prod | LLM + Agent + 多轮对话 + 上下文 | ~95% | ~$0.03 | 生产级，高准确率 |
| global | LLM + RAG + 多语言 | ~95% | ~$0.05 | 多语言支持 |

#### staging+ profile 实现方案

```python
class TextToSQLEngine:
    def generate_sql(self, question: str) -> dict:
        # 1. 检索相关Schema（从元数据目录，不碰数据行）
        schema_context = self.metadata_store.search(question)

        # 2. 检索相似历史查询
        few_shots = self.query_history.search(question, top_k=3)

        # 3. 1次LLM调用：问题 → SQL
        sql = self.llm.generate(
            prompt=self._build_prompt(question, schema_context, few_shots),
            max_tokens=500
        )

        # 4. SQL语法验证 + 安全检查
        sql = self._validate(sql)

        return {"question": question, "sql": sql}
```

### 3.2 智能分析（异常解释）

**LLM的角色：解释器 — 统计方法发现异常，LLM生成人类可读的解释。**

```
数据平面（统计方法，$0，毫秒级）:
  · 3σ检测发现: 华东区今日订单量下降42%
  · IQR检测发现: 电子产品品类退货率异常升高
  · 趋势检测发现: 新客转化率连续3天下降

控制平面（LLM，1次调用，~$0.02，2-5秒）:
  输入: 异常列表 + 相关上下文（血缘、历史异常、业务日历）
  输出: "华东区订单量下降42%，可能原因：
         1. 今日为巴西节假日（圣体节），历史同期也有类似下降
         2. 主要竞品开展618预热促销
         建议确认节假日影响后，关注明日恢复情况。"
```

**关键：异常检测是统计方法做的（$0），LLM只负责把异常列表翻译成人类可读的解释（1次调用）。**

### 3.3 智能治理（元数据补全）

**LLM的角色：描述生成器 — 为表/列生成业务描述，而不是检查数据。**

```
数据平面（自动扫描，$0）:
  · 扫描到新表: fct_daily_revenue
  · 列: order_date, region, category, net_revenue, order_count, avg_delivery_days

控制平面（LLM，1次调用/表，~$0.01）:
  输入: 表名 + 列名 + 列类型 + 样本数据3行
  输出:
    表描述: "日度收入汇总表，按地区和品类聚合，包含收入、订单量、配送时效等指标"
    列描述:
      - order_date: "统计日期"
      - net_revenue: "净收入（扣除退款后的实付金额）"
      - avg_delivery_days: "平均配送天数"
```

**成本分析**：假设500个表，每个表1次LLM调用，总计~$5（一次性），后续增量更新几乎为零。

### 3.4 智能开发（代码生成）

**LLM的角色：代码生成器 — 根据需求生成ETL代码，而不是处理数据。**

```
用户: "我需要一个计算用户近30天消费金额的特征"
     │
     ▼  ← LLM：1次调用，生成SQL
     │
生成代码:
  SELECT
    user_id,
    SUM(total_amount) AS user_30d_purchase_amount,
    CURRENT_DATE AS feature_date
  FROM detail_order
  WHERE order_status = 'completed'
    AND order_time >= CURRENT_DATE - INTERVAL '30' DAY
  GROUP BY user_id
```

---

## 4. 数据平面：确定性方法处理大数据

### 4.1 数据质量检查

**完全不用LLM，用SQL规则 + 统计方法。**

```sql
-- 完整性检查: 主键非空
SELECT COUNT(*) AS null_count FROM detail_order WHERE order_id IS NULL;

-- 唯一性检查: 主键唯一
SELECT order_id, COUNT(*) AS cnt
FROM detail_order
GROUP BY order_id HAVING cnt > 1;

-- 准确性检查: 金额非负
SELECT COUNT(*) AS negative_count FROM detail_order WHERE total_amount < 0;

-- 一致性检查: 明细总额 = 汇总额
SELECT
  ABS((SELECT SUM(total_amount) FROM detail_order) -
      (SELECT SUM(net_revenue) FROM fct_daily_revenue)) AS diff;

-- 时效性检查: 数据新鲜度
SELECT CURRENT_TIMESTAMP - MAX(order_time) AS data_age FROM detail_order;
```

**性能**：100万行，DuckDB执行 < 100ms，成本 $0。

### 4.2 异常检测

**完全不用LLM，用统计方法。**

```python
import numpy as np

class StatisticalAnomalyDetector:

    def detect_3sigma(self, values: np.ndarray) -> list[int]:
        mean = np.mean(values)
        std = np.std(values)
        threshold = 3 * std
        anomalies = np.where(np.abs(values - mean) > threshold)[0]
        return anomalies.tolist()

    def detect_iqr(self, values: np.ndarray) -> list[int]:
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        anomalies = np.where((values < lower) | (values > upper))[0]
        return anomalies.tolist()

    def detect_trend_change(self, values: np.ndarray, window: int = 7) -> list[int]:
        rolling_mean = np.convolve(values, np.ones(window)/window, mode='valid')
        diff = np.diff(rolling_mean)
        threshold = 2 * np.std(diff)
        change_points = np.where(np.abs(diff) > threshold)[0]
        return change_points.tolist()
```

**性能**：100万个数据点，< 50ms，成本 $0。

### 4.3 PII识别

**不用LLM，用正则表达式 + 小型NER模型。**

```python
import re

class PIIDetector:
    PATTERNS = {
        'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
        'phone_cn': re.compile(r'1[3-9]\d{9}'),
        'id_card_cn': re.compile(r'[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]'),
        'credit_card': re.compile(r'\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}'),
    }

    def scan_column(self, values: list[str], sample_size: int = 1000) -> dict:
        results = {}
        sample = values[:sample_size]
        for pii_type, pattern in self.PATTERNS.items():
            matches = sum(1 for v in sample if v and pattern.search(str(v)))
            if matches > 0:
                results[pii_type] = {
                    'match_rate': matches / len(sample),
                    'severity': 'high' if matches / len(sample) > 0.1 else 'low'
                }
        return results
```

**性能**：100万行采样1000行，< 100ms，成本 $0。NER模型（如spaCy）处理1000行 < 1秒。

**为什么不用LLM做PII识别？**

| 方法 | 100万行成本 | 100万行延迟 | 准确率 |
|------|-----------|-----------|--------|
| 正则 + 采样NER | $0 | < 1秒 | 95%+ |
| LLM逐行扫描 | ~$5000 | 数小时 | 98% |

正则+NER的95%准确率已经足够（PII识别是防御性的，宁可漏检少量再人工补充），而成本差5000倍。

### 4.4 业务模型（传统ML）

**不用LLM，用传统ML模型。**

| 场景 | 模型 | 推理方式 | 100万行成本 | 100万行延迟 |
|------|------|---------|-----------|-----------|
| 销量预测 | LightGBM / Prophet | 批量推理 | $0 | < 10秒 |
| 流失预测 | XGBoost | 批量推理 | $0 | < 5秒 |
| 客户分群 | K-Means / DBSCAN | 批量推理 | $0 | < 30秒 |
| 异常交易 | Isolation Forest | 批量推理 | $0 | < 10秒 |
| 商品推荐 | 双塔模型 | 在线推理 | $0 | < 50ms/请求 |

**为什么不用LLM做预测/推荐？**

1. **成本**：LLM推理1次~$0.01，100万次~$10000；LightGBM推理100万次$0
2. **延迟**：LLM推理1次1-3秒；LightGBM推理1次<1ms
3. **确定性**：LLM输出不稳定；传统ML输出确定性
4. **可解释**：传统ML有SHAP/LIME；LLM是黑盒
5. **可优化**：传统ML可以针对业务目标优化；LLM不能

---

## 5. 特征存储与MLOps

### 5.1 特征存储（Feature Store）

特征存储是数据平面和ML模型之间的桥梁。

```
数据平面                    Feature Store                ML模型
─────────                  ─────────────                ──────
Detail Zone ──SQL特征计算──→ 离线特征存储(Iceberg) ──→ 模型训练
                            在线特征存储(Redis)   ──→ 在线推理
                            特征目录(元数据)      ──→ 特征发现
```

#### 特征定义示例

```yaml
feature:
  name: user_30d_purchase_amount
  display_name: "用户近30天消费金额"
  owner: team-ml
  entity_key: user_id

  offline_definition:
    type: sql
    sql: |
      SELECT user_id, SUM(total_amount) AS user_30d_purchase_amount
      FROM detail_order
      WHERE order_status = 'completed'
        AND order_time >= CURRENT_DATE - INTERVAL '30' DAY
      GROUP BY user_id

  online_definition:
    type: stream
    source: kafka_order_events
    aggregation: sum
    window: 30d

  data_type: decimal(12,2)
  statistics:
    mean: 1250.50
    null_rate: 0.02

  lineage:
    upstream: [detail_order.total_amount, detail_order.order_status]
    downstream_models: [user_churn_prediction, product_recommendation]
```

### 5.2 MLOps全流程

```
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ 特征工程  │ → │ 模型训练  │ → │ 模型评测  │ → │ 模型部署  │
│ SQL/Py  │   │LightGBM │   │ 离线评测 │   │ 批量推理 │
└─────────┘   └─────────┘   └─────────┘   └─────────┘
                                                  │
┌─────────┐   ┌─────────┐   ┌─────────┐          │
│ 模型迭代  │ ← │ 告警响应  │ ← │ 模型监控  │ ←────────┘
│ 重训练   │   │ 人工确认  │   │ 统计方法 │
└─────────┘   └─────────┘   └─────────┘
```

**关键：监控也用统计方法，不用LLM。**

- 数据漂移检测：PSI（Population Stability Index），SQL计算
- 模型性能监控：AUC/F1/MAPE，确定性计算
- 特征分布监控：KL散度/JS散度，SQL计算

### 5.3 模型推理架构

```
┌──────────────────────────────────────────────────────────────┐
│                     模型推理架构                                │
│                                                              │
│  离线推理 (Batch)                                             │
│  · 触发: Dagster定时任务 (每日/每周)                           │
│  · 输入: Feature Store离线特征 (Iceberg/Parquet)              │
│  · 推理: LightGBM/XGBoost批量预测                             │
│  · 输出: 写回App Zone (Parquet)                               │
│  · 成本: $0 (本地计算)                                        │
│  · 用例: 用户分群、流失评分、销量预测                           │
│                                                              │
│  在线推理 (Real-time)                                         │
│  · 触发: API请求 / 事件驱动                                   │
│  · 输入: Feature Store在线特征 (Redis, <5ms)                  │
│  · 推理: ONNX Runtime (<10ms)                                │
│  · 输出: REST API返回                                         │
│  · 成本: $0 (本地计算)                                        │
│  · 用例: 商品推荐、实时风控                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. 业务模型场景

### 6.1 场景优先级

| 优先级 | 场景 | 模型 | 数据来源 | 业务价值 | 实施阶段 |
|--------|------|------|---------|---------|---------|
| P0 | 销量预测 | LightGBM时序 | fct_daily_revenue | 库存优化 | Phase 2 |
| P0 | 用户流失预测 | XGBoost | app_customer_360 + 特征 | 降低流失率 | Phase 2 |
| P1 | 客户分群 | K-Means | RFM特征 | 精准营销 | Phase 2 |
| P1 | 情感分析 | 微调BERT小模型 | 评论文本 | 产品改进 | Phase 2-3 |
| P2 | 商品推荐 | 双塔模型 | 行为序列+商品特征 | 提升GMV | Phase 3 |
| P2 | 异常交易检测 | Isolation Forest | 交易特征 | 风控反欺诈 | Phase 3 |

### 6.2 销量预测模型详细设计

```yaml
model:
  name: sales_forecast
  version: "1.0.0"
  owner: team-ml-commerce

  problem_type: time_series_forecasting
  target: daily_sales_quantity
  granularity: [product_category, region]
  forecast_horizon: [7d, 30d]

  features:
    - sales_lag_1d, sales_lag_7d, sales_lag_30d
    - sales_rolling_mean_7d, sales_rolling_std_7d
    - day_of_week, day_of_month, month, is_holiday, is_promotion
    - promotion_discount_rate

  model_config:
    algorithm: lightgbm
    hyperparameters:
      num_leaves: 63
      learning_rate: 0.05
      n_estimators: 500

  evaluation:
    metrics:
      - name: mape
        threshold: 15%
      - name: wmape
        threshold: 10%

  serving:
    type: batch
    schedule: "0 2 * * *"
    output_table: app_sales_forecast
```

### 6.3 模型输出回写数据湖

模型推理结果作为新的数据资产回写到App Zone：

```
App Zone 新增表:
  ├── app_user_churn_score       # 用户流失评分 (LightGBM, 每日批量)
  ├── app_sales_forecast         # 销量预测 (LightGBM, 每日批量)
  ├── app_customer_segment       # 客户分群 (K-Means, 每周批量)
  └── app_anomaly_transactions   # 异常交易 (Isolation Forest, 每日批量)
```

**这些表享有与普通数据同等的治理**：有数据契约、有质量规则、有血缘追踪。

---

## 7. AI与数据闭环

### 7.1 闭环架构

```
数据平台 ──SQL特征──→ Feature Store ──→ 模型训练 ──→ 模型推理
   ↑                                              │
   │                                              ▼
   └──── 推理结果回写App Zone ←── 批量推理结果 ←──┘

闭环1: 模型输出 → 新特征 → 模型优化
  例: 流失评分 → 挽留效果 → 新特征 → 重训练

闭环2: 统计监控 → 漂移告警 → 触发重训练
  例: PSI > 0.2 → 自动告警 → 人工确认重训练

闭环3: 用户反馈 → 标注数据 → 模型优化
  例: 推荐结果 → 用户点击/忽略 → 重训练
```

### 7.2 自动重训练触发

| 触发条件 | 检测方式 | 成本 | 动作 |
|---------|---------|------|------|
| 数据漂移 (PSI>0.2) | SQL计算PSI | $0 | 告警 + 人工确认重训练 |
| 模型性能下降 (>5%) | SQL计算指标 | $0 | 告警 + 人工确认重训练 |
| 新数据积累 (>30天) | 定时检查 | $0 | 自动重训练 + 人工评审 |

**关键：触发检测用SQL/统计方法（$0），不用LLM。**

---

## 8. LLM使用策略

### 8.1 LLM适用场景清单

| 场景 | 激活profile | 调用频率 | 单次成本 | 月度成本 | 价值 |
|------|------------|---------|---------|---------|------|
| Text-to-SQL | staging+ | ~100次/天 | ~$0.01 | ~$30 | 取数效率10x |
| 异常解释 | staging+ | ~10次/天 | ~$0.02 | ~$6 | 排障效率5x |
| 元数据描述 | staging+ | ~50次/月(增量) | ~$0.01 | ~$0.5 | 元数据覆盖率 |
| 代码生成 | staging+ | ~20次/天 | ~$0.02 | ~$12 | 开发效率3x |
| 报告生成 | prod+ | ~5次/天 | ~$0.05 | ~$7.5 | 报告效率5x |
| RAG分析 | global | ~50次/天 | ~$0.05 | ~$75 | 智能分析5x |
| **总计（staging）** | | | | **~$48/月** | |
| **总计（prod）** | | | | **~$112/月** | |
| **总计（global）** | | | | **~$173/月** | |

注：dev profile完全不调用LLM，使用模板匹配（$0）。

### 8.2 LLM不适用场景清单

| 场景 | 错误做法 | 正确做法 | 成本差 |
|------|---------|---------|--------|
| 数据质量检查 | LLM逐行检查 | SQL规则 | 10000x |
| PII识别 | LLM逐行扫描 | 正则+NER | 5000x |
| 异常检测 | LLM判断 | 统计方法 | ∞ (LLM不可行) |
| 销量预测 | LLM预测 | LightGBM | 1000x |
| 推荐排序 | LLM排序 | 双塔模型 | 1000x |
| 数据分类 | LLM分类 | 规则+小模型 | 500x |

### 8.3 LLM成本控制

| 策略 | 说明 | 预期节省 |
|------|------|---------|
| 模板优先 | Phase 1用模板匹配，0 LLM调用 | 100% |
| 缓存 | 相同问题缓存SQL | 30-50% |
| 小模型路由 | 简单问题用小模型(如Qwen-7B) | 50-70% |
| Prompt精简 | 减少不必要的上下文 | 20-30% |
| 本地部署 | 高频场景部署本地小模型 | API费用→$0 |

---

## 9. 技术选型

### 9.1 数据平面技术栈（处理大数据，$0）

| 组件 | 选型 | 用途 | 成本 |
|------|------|------|------|
| 质量检查 | SQL (DuckDB) | 规则引擎 | $0 |
| 异常检测 | NumPy/SciPy | 统计方法 | $0 |
| PII识别 | 正则 + spaCy NER | 模式匹配 | $0 |
| 销量预测 | LightGBM | 时序预测 | $0 |
| 流失预测 | XGBoost | 二分类 | $0 |
| 客户分群 | scikit-learn | 聚类 | $0 |
| 推理服务 | ONNX Runtime | 高性能推理 | $0 |
| 特征存储 | Feast | 离线+在线特征 | $0 |
| 实验追踪 | MLflow | 训练管理 | $0 |

### 9.2 控制平面技术栈（处理交互，按需付费）

| 组件 | 选型 | 用途 | 成本 |
|------|------|------|------|
| Text-to-SQL | GPT-4o-mini / Qwen | SQL生成 | ~$0.01/次 |
| 异常解释 | GPT-4o-mini / Qwen | 解释生成 | ~$0.02/次 |
| 元数据补全 | GPT-4o-mini / Qwen | 描述生成 | ~$0.01/次 |
| 代码生成 | GPT-4o / Qwen-Coder | ETL代码 | ~$0.02/次 |

### 9.3 dev profile技术栈（全部$0）

| 组件 | 选型 | 说明 |
|------|------|------|
| 质量检查 | DuckDB SQL | 本地执行 |
| 异常检测 | NumPy | 本地执行 |
| PII识别 | 正则表达式 | 本地执行 |
| 智能取数 | 模板匹配 | 0 LLM调用 |
| 模型训练 | scikit-learn + LightGBM | 本地训练 |
| 推理服务 | FastAPI + joblib | 本地推理 |

---

## 10. AI能力按profile渐进激活

### 10.1 dev profile：确定性方法 + 模板匹配（$0）

| 能力 | 实现方式 | LLM调用 | 成本 |
|------|---------|---------|------|
| 数据质量检查 | SQL规则 | 0 | $0 |
| 异常检测 | 3σ/IQR统计方法 | 0 | $0 |
| PII识别 | 正则表达式 | 0 | $0 |
| 智能取数 | 模板匹配(20+模板) | 0 | $0 |
| 根因追踪 | 血缘反向追踪 | 0 | $0 |

**dev profile 完全不调用LLM，零AI成本。适合Demo演示和概念验证。**

### 10.2 staging profile：引入LLM交互 + 传统ML模型

| 能力 | 实现方式 | LLM调用 | 月成本 |
|------|---------|---------|--------|
| 智能取数升级 | LLM生成SQL | ~3000次/月 | ~$30 |
| 异常解释 | LLM生成解释 | ~300次/月 | ~$6 |
| 元数据补全 | LLM生成描述 | ~50次/月 | ~$0.5 |
| 代码生成 | LLM生成ETL代码 | ~600次/月 | ~$12 |
| 销量预测 | LightGBM | 0 | $0 |
| 流失预测 | XGBoost | 0 | $0 |
| 客户分群 | K-Means | 0 | $0 |
| Feature Store | Feast | 0 | $0 |

**staging profile LLM月成本 ~$48，传统ML $0。**

### 10.3 prod profile：完整AI栈 + MLOps

| 能力 | 实现方式 | LLM调用 | 月成本 |
|------|---------|---------|--------|
| 智能取数 | LLM + Agent | ~3000次/月 | ~$90 |
| 异常解释 | LLM + 上下文增强 | ~300次/月 | ~$9 |
| 元数据补全 | LLM + 自动分类 | ~50次/月 | ~$0.5 |
| 代码生成 | LLM生成ETL代码 | ~600次/月 | ~$12 |
| 商品推荐 | 双塔模型 | 0 | $0 |
| 异常交易 | Isolation Forest | 0 | $0 |
| 模型监控 | 统计方法（PSI/AUC） | 0 | $0 |
| MLOps | MLflow | 0 | $0 |

**prod profile LLM月成本 ~$112，传统ML $0。**

### 10.4 global profile：AI闭环 + 高级模型

| 能力 | 实现方式 | LLM调用 | 月成本 |
|------|---------|---------|--------|
| RAG分析助手 | LLM + 向量检索 | ~1500次/月 | ~$75 |
| 智能报告 | LLM生成报告 | ~150次/月 | ~$7.5 |
| 多语言NL2SQL | LLM + 翻译 + 模板 | ~3000次/月 | ~$90 |
| 自动重训练 | 统计触发 + 自动化 | 0 | $0 |
| 跨区域Feature Store | Feast多区域 | 0 | $0 |
| 模型输出治理 | 数据契约+质量规则 | 0 | $0 |
| 在线推理服务 | ONNX Runtime | 0 | $0 |

**global profile LLM月成本 ~$173，传统ML $0。**

---

## 11. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LLM生成SQL不正确 | 中 | 中 | SQL验证+执行计划分析+结果合理性检查 |
| LLM成本超预期 | 低 | 中 | 缓存+小模型路由+月度预算硬顶 |
| 传统ML模型效果不达预期 | 中 | 高 | 从简单模型开始，设定最低效果标准，逐步迭代 |
| 训练-服务偏差 | 中 | 高 | Feature Store统一离线/在线特征逻辑 |
| 模型衰退 | 高 | 中 | 统计方法监控+自动告警+重训练机制 |
| 过度依赖LLM | 中 | 高 | 严格区分两个平面，LLM只用于控制平面 |
