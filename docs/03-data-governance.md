# DataMind 弹性治理体系

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v3.0 | 2026-05-11 | DataMind Team | 重新设计：治理能力按剖面分级 |

---

## 1. 治理理念：剖面驱动的治理

治理不是全或无的开关，而是**随规模增长逐步激活的梯度**：

```
dev:       基础质量，约定为主，告警不阻塞
staging:   自动化检查，CI/CD门禁
prod:      完整治理，质量阻塞写入，指标认证
global:    多区域合规，数据驻留强制执行
```

---

## 2. 治理能力矩阵

| 治理能力 | dev | staging | prod | global | 实现方式 |
|---------|-----|---------|------|--------|---------|
| 数据质量规则 | warn | warn | block | block | 同一份YAML，severity按profile不同 |
| Schema契约检查 | 手动 | CI自动 | 写入前强制 | 写入前强制 | dbt post-hook |
| 元数据目录 | 无 | PostgreSQL | OpenMetadata | 多区域同步 | MetadataInterface |
| 数据血缘 | 无 | dbt自动 | SQL解析 | 跨区域追踪 | 自动采集 |
| 指标认证 | 无 | Bronze | Silver | Gold | 渐进升级 |
| PII检测 | 无 | 手动 | 自动采样 | 自动全量 | 正则+NER |
| 列级脱敏 | 无 | 无 | 数据代理 | 多区域合规 | 数据访问代理 |
| 审计日志 | 无 | 文件 | 结构化 | 不可篡改 | 审计接口 |

---

## 3. 数据质量

### 3.1 六维质量模型（所有剖面一致）

| 维度 | 典型规则 | dev | staging | prod |
|------|---------|-----|---------|------|
| 完整性 | 主键非空 | warn | warn | block |
| 准确性 | 金额≥0 | warn | warn | block |
| 唯一性 | 主键唯一 | warn | warn | block |
| 一致性 | 明细=汇总 | warn | warn | warn |
| 时效性 | 数据延迟<1h | warn | warn | alert |
| 合规性 | PII脱敏 | — | warn | block |

### 3.2 规则定义（一份YAML，多剖面行为）

```yaml
quality_rules:
  - name: "订单主键非空"
    sql: "SELECT COUNT(*) FROM {table} WHERE order_id IS NULL"
    expectation: "= 0"
    severity:
      dev: warn
      staging: warn
      prod: block
```

**检查频率**：dev手动运行；staging CI/CD每次PR运行；prod每次ETL写入后运行。

---

## 4. 数据血缘

| 剖面 | 采集方式 | 粒度 | 存储 |
|------|---------|------|------|
| dev | 无 | — | — |
| staging | dbt `ref()` 自动解析 | 表级 | PostgreSQL |
| prod | SQL解析 + 执行计划 | 字段级 | OpenMetadata |
| global | 跨区域追踪 | 字段级 | 全局控制平面 |

---

## 5. 指标管理

| 级别 | 含义 | 最低剖面 | 要求 |
|------|------|---------|------|
| Bronze | 已定义 | staging | 有SQL定义 + 所有者 |
| Silver | 已验证 | prod | 质量门禁通过 + 业务确认 |
| Gold | 已认证 | global | 财务认证 + 变更审批 |

---

## 6. 安全合规

| 能力 | dev | staging | prod | global |
|------|-----|---------|------|--------|
| 认证 | 无 | API Key | SSO+OIDC | SSO+MFA |
| 授权 | 无 | 基础RBAC | RBAC+列级 | RBAC+ABAC |
| PII检测 | 无 | 手动 | 自动采样 | 自动全量+NER |
| 脱敏 | 无 | 无 | 数据代理 | 多法规自动 |
| 加密 | 无 | TLS | TLS+存储 | 全链路+KMS |
| 审计 | 无 | 文件日志 | 结构化 | 不可篡改 |
| 合规 | 无 | 无 | GDPR/个保法 | 多法规自动 |