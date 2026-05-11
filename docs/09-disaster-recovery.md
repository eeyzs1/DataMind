# DataMind 容灾与高可用

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v1.0 | 2026-05-11 | DataMind Team | 初始版本 |
| v3.0 | 2026-05-11 | DataMind Team | 重写为弹性框架：profile驱动的灾备策略 |

---

## 1. 设计理念：profile驱动的弹性灾备

### 1.1 核心原则

数据平台的容灾与传统应用不同。传统应用的核心是"备份恢复"，数据平台的核心是**"可重算"**：

```
传统应用容灾: 备份 → 恢复 → 服务可用
数据平台容灾: 保护Raw → 重算下游 → 全链路恢复
```

只要Raw Zone的数据零丢失，所有下游数据都可以通过幂等ETL重算恢复。因此容灾的核心是**保护Raw Zone**。

### 1.2 弹性灾备理念

灾备不是全有或全无。Demo阶段不需要异地多活，但框架必须支持平滑升级。

```
dev profile       staging profile     prod profile        global profile
───────────      ───────────────     ─────────────       ──────────────
零灾备           基础备份             企业灾备             全球灾备
(Git版本控制)     (快照+备份)          (跨AZ+自动恢复)       (多区域+自动切换)
```

### 1.3 灾备目标（随profile升级）

| 目标 | dev | staging | prod | global |
|------|-----|---------|------|--------|
| Raw Zone RPO | N/A（无保护） | 24小时（每日备份） | **0**（Iceberg快照+跨AZ复制） | **0**（多区域同步） |
| 下游数据 RPO | N/A | 可重算 | 可重算（ETL幂等） | 可重算 |
| Raw Zone RTO | N/A | 4小时（手动恢复） | 1小时（快照回滚） | 15分钟（自动切换） |
| 服务可用性 | N/A | 99%（单实例） | 99.9%（跨AZ） | 99.99%（多区域） |

### 1.4 灾备接口抽象

```python
class BackupInterface(ABC):
    @abstractmethod
    def snapshot(self, path: str, metadata: dict = None) -> str: ...
    @abstractmethod
    def restore(self, snapshot_id: str, target_path: str): ...
    @abstractmethod
    def list_snapshots(self, path: str) -> list[dict]: ...
    @abstractmethod
    def cleanup(self, retention_days: int): ...

class FailoverInterface(ABC):
    @abstractmethod
    def health_check(self) -> dict: ...
    @abstractmethod
    def switch_to_standby(self, region: str = None) -> bool: ...
    @abstractmethod
    def status(self) -> dict: ...
```

---

## 2. 灾备能力渐进矩阵

### 2.1 灾备能力总览

| 灾备能力 | dev | staging | prod | global |
|---------|-----|---------|------|--------|
| 代码版本控制 | ✅ Git | ✅ Git | ✅ Git | ✅ Git |
| 数据快照 | ❌ | ✅ Iceberg快照（每日） | ✅ Iceberg快照（每小时） | ✅ Iceberg快照（每小时+跨区域） |
| 数据备份 | ❌ | ✅ Raw Zone备份到远端 | ✅ 跨AZ复制Raw Zone | ✅ 多区域同步Raw Zone |
| ETL幂等 | ⚠️ 手动保证 | ✅ dbt test验证 | ✅ 自动测试 | ✅ 自动测试+混沌工程 |
| 服务高可用 | ❌ 单进程 | ⚠️ 单实例+自动重启 | ✅ 跨AZ+K8s自愈 | ✅ 多区域+自动切换 |
| 降级策略 | ❌ | ❌ | ✅ 三级降级（实时→近线→缓存） | ✅ 多级降级+区域切换 |
| 熔断规则 | ❌ | ❌ | ✅ 服务级熔断 | ✅ 智能熔断+自适应 |
| 容灾演练 | ❌ | ❌ | ✅ 季度演练 | ✅ 月度自动化演练 |

### 2.2 profile.yaml 灾备配置

```yaml
disaster_recovery:
  snapshot:
    enabled: false            # staging+: true
    frequency: "0 * * * *"    # staging=daily(0 2 * * *), prod=hourly(0 * * * *)
    retention_hours: 72       # 快照保留时间

  backup:
    enabled: false            # staging+: true
    targets: ["raw"]          # 只备份Raw Zone（下游可重算）
    destination: ""           # staging=remote_minio, prod=s3_cross_az, global=s3_cross_region

  failover:
    mode: none                # dev=none, staging=manual, prod=auto_az, global=auto_region
    max_downtime_seconds: 3600

  etl_idempotency:
    enforced: false           # prod+: true
    test_on_deploy: false     # prod+: true

  drills:
    enabled: false            # prod+: true
    schedule: "0 10 1 */3 *"  # prod=quarterly, global=monthly
```

---

## 3. 数据层容灾：分层保护策略

### 3.1 保护优先级

```
保护优先级（所有profile一致）:

  最高: Raw Zone        → 原始数据不可重算，必须备份
  次高: 元数据目录       → 元数据不可丢失，必须同步复制
  中:   Cleaned/Detail  → 可从Raw重算，备份可选
  最低: Summary/App     → 可从Detail重算，不需要备份
```

### 3.2 Raw Zone保护策略（按profile）

| profile | 保护方式 | RPO | RTO | 说明 |
|---------|---------|-----|-----|------|
| **dev** | 无 | ∞ | ∞ | 本地文件，Git管理配置 |
| **staging** | MinIO镜像到远端 | 24小时 | 4小时 | 每日rsync，手动恢复 |
| **prod** | Iceberg快照 + 跨AZ S3复制 | 0 | 1小时 | 每小时快照，S3跨AZ自动复制 |
| **global** | Iceberg快照 + 跨区域S3复制 | 0 | 15分钟 | 每区域独立快照，异步跨区域复制 |

```
prod profile 容灾架构:

主AZ                                  灾备AZ
┌──────────────┐                      ┌──────────────┐
│  Raw Zone    │  ──异步复制──→       │  Raw Zone    │
│  (Iceberg)   │  (S3跨AZ，延迟<1min) │  (Iceberg)   │
│              │                      │              │
│  Cleaned     │                      │  Cleaned     │
│  Detail      │  ──不复制──→         │  (空，需重算)  │
│  Summary     │  (可从Raw重算)        │              │
│  App         │                      │  App         │
│              │                      │  (空，需重算)  │
│  元数据       │  ──同步复制──→       │  元数据       │
│  (PostgreSQL)│  (Multi-AZ，实时)     │  (PostgreSQL)│
└──────────────┘                      └──────────────┘
```

**关键决策：只复制Raw数据和元数据，下游数据通过ETL幂等重算恢复。** 这节省了90%的灾备存储和带宽成本。

### 3.3 Iceberg快照策略（staging+ profile）

| 参数 | staging | prod | global |
|------|---------|------|--------|
| 快照频率 | 每日 | 每小时 | 每小时 |
| 快照保留 | 7天 | 72小时（自动过期） | 72小时（本地）+ 30天（远端） |
| 快照存储 | 本地MinIO | S3（同bucket） | S3（区域bucket） |
| 回滚方式 | `ROLLBACK TO SNAPSHOT` | 秒级回滚 | 秒级回滚（区域自治） |

### 3.4 ETL幂等性保证（prod+ profile）

所有ETL任务必须幂等——多次运行结果一致。这是"可重算"容灾策略的基础。

| 方式 | 说明 | 适用场景 |
|------|------|---------|
| 覆盖写入 | `CREATE OR REPLACE TABLE` | 全量刷新的汇总表 |
| 增量合并 | `MERGE INTO` (Iceberg) | 增量更新的明细表 |
| 事务写入 | Iceberg原子提交 | 所有表 |
| 去重保证 | 主键去重 + 幂等标记 | 所有表 |

```python
# CI/CD 中自动验证ETL幂等性
def test_etl_idempotency(pipeline_name: str):
    # 第一次运行
    result1 = execute_pipeline(pipeline_name)
    # 第二次运行（相同输入）
    result2 = execute_pipeline(pipeline_name)
    # 结果必须一致
    assert result1.equals(result2), f"Pipeline {pipeline_name} is NOT idempotent!"
```

---

## 4. 服务层容灾

### 4.1 服务高可用（按profile）

| 服务 | dev | staging | prod | global |
|------|-----|---------|------|--------|
| DuckDB/Spark | 单进程 | 单实例 | 集群（Master HA） | 多区域集群 |
| PostgreSQL | SQLite | 单实例 | Multi-AZ（同步复制） | 区域Multi-AZ + 跨区域读取 |
| FastAPI | 单进程 | Docker重启策略 | K8s水平扩展 | 多区域K8s + CDN |
| Dagster | APScheduler | Docker重启策略 | K8s集群 | 多区域Dagster |
| Superset | Streamlit | Docker重启策略 | K8s集群 | 多区域Superset |
| MinIO/S3 | 本地FS | 纠删码 | S3（11个9s持久性） | 多区域S3 |

### 4.2 降级策略（prod+ profile）

```
正常状态                    降级状态                     严重降级
┌──────────┐              ┌──────────┐               ┌──────────┐
│ 实时数据   │  ──降级──→  │ 近线数据   │  ──降级──→   │ 缓存数据   │
│ (延迟<1m) │              │ (延迟<1h) │               │ (最近快照) │
└──────────┘              └──────────┘               └──────────┘
                                │                         │
                                │ 恢复                     │ 恢复
                                ▼                         ▼
                           ┌──────────┐              ┌──────────┐
                           │ 实时数据   │              │ 近线数据   │
                           └──────────┘              └──────────┘
```

**降级触发条件**：

| 级别 | 触发条件 | 降级措施 | 恢复条件 |
|------|---------|---------|---------|
| 实时→近线 | 实时管线延迟>5分钟 | 大屏显示近线数据，标注"数据延迟" | 实时管线恢复正常 |
| 近线→缓存 | 近线数据延迟>1小时 | 显示最近缓存数据，标注"数据可能过时" | 近线数据恢复正常 |
| 缓存→维护 | 缓存数据过期(>24小时) | 显示维护页面 | 系统恢复 |
| 区域→灾备（global专属） | 主区域不可用>5分钟 | DNS切换到灾备区域 | 主区域恢复 |

### 4.3 熔断规则（prod+ profile）

| 服务 | 熔断条件 | 熔断行为 | 恢复条件 |
|------|---------|---------|---------|
| 数据API | 错误率>10%持续1分钟 | 返回缓存数据 | 错误率<1%持续3分钟 |
| Superset | 响应时间>10秒持续2分钟 | 降级到简化视图 | 响应时间<3秒持续5分钟 |
| 大屏 | 数据源不可用 | 显示最后缓存数据 | 数据源恢复 |
| ETL任务 | 连续失败3次 | 暂停调度，告警 | 人工确认后恢复 |

---

## 5. 全球灾备架构（global profile专属）

### 5.1 多区域部署模型

```
                    ┌─────────────────────────┐
                    │    全局控制平面           │
                    │  · 健康检查（所有区域）    │
                    │  · 自动切换决策           │
                    │  · DNS/路由更新           │
                    └──────┬──────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
  ┌─────▼─────┐      ┌─────▼─────┐      ┌─────▼─────┐
  │  区域: 中国  │      │  区域: 欧洲  │      │  区域: 北美  │
  │  (主)      │      │  (主)      │      │  (灾备)    │
  │            │      │            │      │            │
  │ · Raw副本  │      │ · Raw副本  │      │ · Raw副本  │
  │ · 全量计算 │      │ · 全量计算 │      │ · 待命计算  │
  │ · 在线服务 │      │ · 在线服务 │      │ · 在线服务  │
  └───────────┘      └───────────┘      └───────────┘
```

### 5.2 区域故障切换

```
1. 全局控制平面检测到中国区域不可用（健康检查连续失败3次，持续5分钟）
     │
     ▼
2. 自动切换决策
   ├── 确认: 非网络抖动（3次检查均失败）
   ├── 决策: 将中国区域流量切换到亚太灾备区域
   └── 通知: 所有值班人员收到P0告警
     │
     ▼
3. 执行切换
   ├── DNS: 中国区域域名 → 亚太灾备区域IP
   ├── API: 全局API路由更新
   └── 数据: 灾备区域从最新Iceberg快照启动
     │
     ▼
4. 恢复验证
   ├── 服务可用性检查
   ├── 数据新鲜度检查（快照时间）
   └── 通知用户："服务已恢复，数据延迟约15分钟"
```

### 5.3 跨区域数据同步

| 数据类型 | 同步方式 | 延迟 | 带宽 |
|---------|---------|------|------|
| Raw Zone | 异步跨区域复制（S3 Cross-Region Replication） | <5分钟 | ~100Mbps/区域 |
| 元数据 | 全局PostgreSQL逻辑复制 | <1秒 | ~1Mbps |
| 下游数据 | 不复制（可重算） | N/A | $0 |
| 聚合缓存 | Redis跨区域异步 | <10秒 | ~10Mbps |

---

## 6. 容灾演练（prod+ profile）

### 6.1 演练计划

| 演练场景 | staging | prod | global |
|---------|---------|------|--------|
| 单服务故障 | 不定期手动 | 每月 | 每两周 |
| 数据层故障 | 不定期手动 | 每季度 | 每月 |
| 单AZ故障 | ❌ | 每季度 | 每季度 |
| 区域故障 | ❌ | ❌ | 每半年 |
| 全链路故障 | ❌ | 每年 | 每半年 |

### 6.2 演练检查清单

- [ ] Raw Zone数据零丢失
- [ ] 元数据目录完整恢复
- [ ] ETL管线可从任意点重算
- [ ] 降级策略正常触发
- [ ] 熔断规则正常生效
- [ ] 告警通知及时送达
- [ ] 恢复后数据质量检查通过
- [ ] 演练过程记录完整（用于RCA）

### 6.3 演练自动化（global profile）

```python
# scripts/dr_drill.py
def automated_dr_drill(scenario: str):
    """
    自动化容灾演练
    scenario: "service_failure" | "data_corruption" | "az_failure" | "region_failure"
    """
    # 1. 记录演练前状态
    pre_state = capture_state()
    
    # 2. 注入故障
    inject_fault(scenario)
    
    # 3. 等待自动恢复
    wait_for_recovery(timeout_seconds=scenario_timeout(scenario))
    
    # 4. 验证恢复结果
    post_state = capture_state()
    violations = compare(pre_state, post_state)
    
    # 5. 生成演练报告
    report = {
        "scenario": scenario,
        "timestamp": datetime.now().isoformat(),
        "recovery_time_seconds": post_state.timestamp - pre_state.timestamp,
        "data_loss_rows": violations.get("data_loss", 0),
        "rpo_met": violations.get("data_loss", 0) == 0,
        "rto_met": recovery_time <= target_rto[scenario],
        "passed": all(v == 0 for v in violations.values())
    }
    
    return report
```

---

## 7. Profile升级灾备检查清单

从较低profile升级到较高profile时，执行以下灾备检查：

| 检查项 | dev→staging | staging→prod | prod→global |
|--------|------------|-------------|------------|
| Raw备份 | 配置MinIO镜像 | 配置Iceberg快照+S3跨AZ | 配置跨区域S3复制 |
| 元数据同步 | 确认备份脚本 | 配置PostgreSQL Multi-AZ | 配置跨区域逻辑复制 |
| ETL幂等 | - | 所有管线CI自动测试幂等 | 增加混沌工程测试 |
| 服务HA | - | K8s部署+健康检查 | 跨区域K8s+自动切换 |
| 降级策略 | - | 配置三级降级 | 增加区域切换 |
| 熔断规则 | - | 配置服务级熔断 | 配置智能熔断 |
| 演练计划 | - | 建立季度演练 | 建立月度自动化演练 |