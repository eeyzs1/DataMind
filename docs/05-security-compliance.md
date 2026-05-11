# DataMind 安全与合规

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|---------|
| v1.0 | 2026-05-11 | DataMind Team | 初始版本 |
| v3.0 | 2026-05-11 | DataMind Team | 重写为弹性框架：profile驱动的安全能力渐进激活 |

---

## 1. 安全设计理念：profile驱动的渐进式安全

### 1.1 核心原则

| 原则 | 含义 | dev | staging | prod | global |
|------|------|-----|---------|------|--------|
| **零信任** | 不信任任何内部请求 | ❌ localhost | ⚠️ 内网信任 | ✅ 全链路验证 | ✅ 跨区域零信任 |
| **最小权限** | 只授予完成任务所需的最小权限 | ❌ 全部权限 | ⚠️ 角色级别 | ✅ RBAC+列级 | ✅ RBAC+ABAC |
| **纵深防御** | 多层安全机制 | ❌ 单层 | ⚠️ 应用层 | ✅ 4层防护 | ✅ 5层+跨区域 |
| **默认安全** | 安全是默认配置 | ❌ 默认开放 | ⚠️ 部分默认 | ✅ 默认安全 | ✅ 全面默认安全 |

### 1.2 弹性安全理念

安全不是全有或全无。Demo阶段不需要KMS和审计日志，但框架必须支持平滑升级。

```
dev profile       staging profile     prod profile        global profile
───────────      ───────────────     ─────────────       ──────────────
零安全           基础安全             企业安全             合规安全
(本地单用户)      (团队内网)          (生产多用户)         (多区域合规)

        升级路径：只改 config/profile.yaml 中的 security 配置块
        业务代码、数据模型、ETL逻辑完全不变
```

### 1.3 安全接口抽象

```python
class AuthInterface(ABC):
    @abstractmethod
    def authenticate(self, credentials: dict) -> 'UserContext': ...
    @abstractmethod
    def authorize(self, user: 'UserContext', resource: str, action: str) -> bool: ...

class MaskingInterface(ABC):
    @abstractmethod
    def apply(self, data: DataFrame, user: 'UserContext', columns: list[str]) -> DataFrame: ...

class AuditInterface(ABC):
    @abstractmethod
    def record(self, event: 'AuditEvent'): ...
    @abstractmethod
    def query(self, filters: dict, limit: int = 100) -> list['AuditEvent']: ...

class EncryptionInterface(ABC):
    @abstractmethod
    def encrypt(self, plaintext: bytes, key_id: str) -> bytes: ...
    @abstractmethod
    def decrypt(self, ciphertext: bytes, key_id: str) -> bytes: ...
```

---

## 2. 安全能力渐进矩阵

### 2.1 安全能力总览

| 安全能力 | dev | staging | prod | global |
|---------|-----|---------|------|--------|
| 认证 | 无（localhost） | SSO (OIDC) | SSO + MFA + 服务账号 | SSO + MFA + 跨区域联邦 |
| 授权 | 无 | 基础RBAC | RBAC + 列级权限 | RBAC + ABAC + 动态授权 |
| 脱敏 | 无 | PII识别规则 | 数据访问代理 + 自动脱敏 | 零信任 + 智能脱敏 + 跨区域 |
| 加密 | 无 | TLS 1.3 | TLS + 存储加密 | 全链路加密 + KMS + HSM |
| 审计 | 文件日志 | 结构化审计日志 | 不可篡改审计 + 异常检测 | 跨区域审计聚合 |
| 合规 | 无 | 基础合规标注 | GDPR/网安法合规 | 多区域合规 + 自动合规检查 |
| 多区域 | 单机 | 单区域 | 单区域（多区域就绪） | 多区域 + 数据驻留 |

### 2.2 profile.yaml 安全配置

```yaml
security:
  auth:
    backend: none              # dev=none, staging=oidc, prod=oidc_mfa
    oidc:
      provider: ""             # staging/prod: "keycloak" / "auth0"
      client_id: ""
    mfa_required: false        # prod: true

  authorization:
    backend: none              # dev=none, staging=rbac, prod=rbac_abac
    column_level: false        # prod: true

  masking:
    backend: none              # dev=none, staging=rule_based, prod=proxy
    default_policy: none       # dev=none, staging=partial, prod=replace

  audit:
    backend: file              # dev=file, staging=structured, prod=immutable
    retention_days: 30         # prod: 2555 (7年)

  encryption:
    at_rest: false             # prod: true
    in_transit: false          # staging: true, prod: true
    field_level: false         # prod: true

  compliance:
    regions: []                # prod: ["CN"], global: ["CN", "EU", "US"]
    frameworks: []             # prod: ["网络安全法"], global: ["GDPR", "CCPA", "网络安全法"]
```

---

## 3. 认证与授权：profile驱动的弹性

### 3.1 认证后端

| profile | 后端实现 | 说明 |
|---------|---------|------|
| **dev** | `NoAuthBackend` | 所有请求视为admin用户 |
| **staging** | `OIDCAuthBackend` | Keycloak/Auth0，团队SSO |
| **prod** | `OIDCWithMFABackend` | SSO + MFA + 服务账号(API Key) |
| **global** | `FederatedAuthBackend` | 跨区域身份联邦 + 区域级别SSO |

```python
# dev backend: 跳过所有认证
class NoAuthBackend(AuthInterface):
    def authenticate(self, credentials: dict) -> UserContext:
        return UserContext(user_id="dev_user", roles=["admin"])
    def authorize(self, user: UserContext, resource: str, action: str) -> bool:
        return True  # dev允许一切操作

# prod backend: 完整认证授权
class OIDCAuthBackend(AuthInterface):
    def authenticate(self, credentials: dict) -> UserContext:
        token = self._verify_jwt(credentials["token"])
        return UserContext(user_id=token.sub, roles=self._resolve_roles(token))
    def authorize(self, user: UserContext, resource: str, action: str) -> bool:
        return self.policy_engine.evaluate(user, resource, action)
```

### 3.2 RBAC + ABAC混合模型（prod profile）

**RBAC（基于角色）**：

| 角色 | 数据范围 | 操作权限 | 脱敏级别 |
|------|---------|---------|---------|
| data_admin | 全部数据集 | 读写+管理 | 无脱敏 |
| data_engineer | 所负责域的数据集 | 读写 | 需审批脱敏 |
| data_analyst | Silver及以上认证数据集 | 只读 | partial脱敏 |
| business_user | Gold认证数据集 | 只读 | replace脱敏 |
| external_user | 明确授权的数据集 | 只读 | hash脱敏 |

**ABAC（基于属性）** — 在RBAC之上叠加属性条件：

```
访问决策 = f(角色, 数据敏感级别, 数据区域, 访问时间, 访问频率, 操作类型)

规则示例:
  · IF 角色=analyst AND 数据敏感级别=confidential AND 区域≠用户所在区域 THEN 拒绝
  · IF 角色=engineer AND 数据包含PII AND 当前时间非工作时间 THEN 需审批
  · IF 角色=any AND 同一用户1小时内导出>10万行 THEN 告警+需审批
  · IF 操作类型=export AND 数据量>1GB THEN 需审批
```

### 3.3 列级权限（prod profile）

```
表: detail_order
┌──────────────┬──────────┬──────────┬──────────┬──────────┐
│     列        │ admin    │ engineer │ analyst  │ viewer   │
├──────────────┼──────────┼──────────┼──────────┼──────────┤
│ order_id     │ ✅ 可见   │ ✅ 可见   │ ✅ 可见   │ ✅ 可见   │
│ user_id      │ ✅ 可见   │ 🔑 hash  │ 🔑 hash  │ ❌ 隐藏   │
│ user_phone   │ ✅ 可见   │ 🔑 需审批 │ 🔑 replace│ ❌ 隐藏   │
│ amount       │ ✅ 可见   │ ✅ 可见   │ ✅ 可见   │ ✅ 可见   │
│ address      │ ✅ 可见   │ 🔑 需审批 │ 🔑 suppress│ ❌ 隐藏  │
│ order_status │ ✅ 可见   │ ✅ 可见   │ ✅ 可见   │ ✅ 可见   │
└──────────────┴──────────┴──────────┴──────────┴──────────┘
```

---

## 4. PII识别与脱敏：profile驱动的弹性

### 4.1 PII识别规则

```yaml
pii_patterns:
  - name: email
    pattern: '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    sensitivity: medium
    masking: partial
  - name: phone_cn
    pattern: '1[3-9]\d{9}'
    sensitivity: medium
    masking: replace
  - name: id_card_cn
    pattern: '[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx]'
    sensitivity: high
    masking: hash
  - name: credit_card
    pattern: '\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}'
    sensitivity: critical
    masking: tokenize
```

### 4.2 脱敏策略（所有profile通用规则定义）

| 策略 | 说明 | 可逆性 | 示例 |
|------|------|--------|------|
| partial | 保留首尾字符，中间替换 | 不可逆 | `j***@gmail.com` |
| replace | 保留部分，其余替换 | 不可逆 | `138****1234` |
| hash | SHA-256哈希 | 不可逆，可关联 | `a3f2b8c...` |
| tokenize | 替换为随机token | 需授权可逆 | `TOK-ABC123` |
| suppress | 完全删除 | 不可逆 | `(null)` |

### 4.3 脱敏执行方式（随profile升级）

| profile | 脱敏方式 | 说明 |
|---------|---------|------|
| **dev** | 不执行 | 本地开发不需要脱敏 |
| **staging** | 应用层规则匹配 | FastAPI中间件，查询返回前执行脱敏 |
| **prod** | 数据访问代理 | 独立代理层，所有查询经过代理，不可绕过 |
| **global** | 区域代理 + 全局策略 | 每个区域有独立代理，策略由全局控制平面下发 |

```
prod profile 脱敏流程:

数据访问请求
     │
     ▼
┌─────────────────────────────────────────────────┐
│           数据访问代理 (Data Access Proxy)         │
│                                                 │
│  1. 认证: 验证用户身份 (JWT验证)                   │
│  2. 授权: 检查用户对目标数据的访问权限              │
│  3. 脱敏: 根据角色×敏感级别执行列级脱敏             │
│  4. 审计: 记录访问日志（不可篡改）                  │
│  5. 异常检测: 检测异常访问模式（统计方法）           │
│                                                 │
│  脱敏规则矩阵:                                    │
│  ┌──────────┬──────────┬──────────┬──────────┐  │
│  │ 角色\级别 │ public   │ internal │confidential│  │
│  ├──────────┼──────────┼──────────┼──────────┤  │
│  │ admin    │ 原文     │ 原文     │ 需审批     │  │
│  │ analyst  │ 原文     │ partial  │ replace   │  │
│  │ viewer   │ 原文     │ replace  │ suppress  │  │
│  │ external │ 原文     │ hash     │ 拒绝      │  │
│  └──────────┴──────────┴──────────┴──────────┘  │
└─────────────────────────────────────────────────┘
```

---

## 5. 审计追踪：profile驱动的弹性

### 5.1 审计后端

| profile | 后端 | 特点 |
|---------|------|------|
| **dev** | 文件日志（JSON Lines） | 够用就行，便于调试 |
| **staging** | 结构化审计日志（SQLite） | 可查询、可统计 |
| **prod** | 不可篡改审计（PostgreSQL + 数字签名） | 合规级别，追加写，签名防篡改 |
| **global** | 多区域聚合（PostgreSQL + 跨区域汇总） | 区域自治 + 全局合规报告 |

### 5.2 审计日志规范（所有profile一致的格式）

```json
{
  "event_id": "evt_abc123",
  "timestamp": "2026-05-11T10:30:00.000Z",
  "event_type": "data_access",
  "actor": {
    "user_id": "u_456",
    "role": "analyst",
    "ip": "10.0.1.100",
    "session_id": "sess_xyz"
  },
  "resource": {
    "type": "table",
    "name": "detail_order",
    "zone": "detail",
    "columns_accessed": ["order_id", "amount"]
  },
  "action": {
    "method": "query",
    "rows_returned": 1500,
    "execution_time_ms": 23
  },
  "context": {
    "pii_accessed": false,
    "masking_applied": [],
    "access_reason": "daily_report"
  },
  "result": "success"
}
```

### 5.3 异常访问检测（prod + global profile）

| 异常模式 | 检测规则 | 检测方式 | 响应 |
|---------|---------|---------|------|
| 大量导出 | 单次导出>10万行 | SQL统计（$0） | 告警 + 需审批 |
| 频繁查询PII | 1小时内查询PII字段>100次 | SQL统计（$0） | 告警 + 临时限制 |
| 非工作时间访问 | 工作时间外访问敏感数据 | 时间规则（$0） | 告警 |
| 异常IP | 从未出现的IP | 规则匹配（$0） | 告警 + 二次验证 |
| 权限提升 | 短时间内申请多个高权限 | 统计检测（$0） | 告警 + 需审批 |

**所有异常检测使用确定性规则和统计方法，不用LLM。**

---

## 6. 数据加密：profile驱动的弹性

| 状态 | dev | staging | prod | global |
|------|-----|---------|------|--------|
| 传输中 | 无 | TLS 1.3 | TLS 1.3 | TLS 1.3 + mTLS |
| 存储中 | 无 | 无 | AES-256 (KMS) | AES-256 (HSM) |
| 特定字段 | 无 | 无 | AES-256-GCM | 区域独立密钥 |

```yaml
# profile.yaml 中加密配置
encryption:
  in_transit:
    enabled: true           # staging+: true
    min_tls_version: "1.3"
  at_rest:
    enabled: false          # prod: true
    algorithm: AES-256
    key_management: kms     # prod=kms, global=hsm
  field_level:
    enabled: false          # prod: true
    rotation_days: 30       # 每月轮换字段加密密钥
```

---

## 7. 多区域合规：global profile专属

### 7.1 区域部署模型（global profile）

```
┌──────────────────────────────────────────────────────────────┐
│                    全局控制平面 (Global Control Plane)          │
│  · 全局元数据目录    · 跨区域血缘追踪    · 统一权限策略下发        │
│  · 全局审计聚合     · 合规策略下发      · 成本归集               │
└──────────┬───────────────────────┬───────────────────────────┘
           │                       │
    ┌──────▼──────┐         ┌──────▼──────┐         ┌──────────┐
    │  区域: 中国   │         │  区域: 欧洲   │         │ 区域: 北美  │
    │             │         │             │         │          │
    │ · 本地存储   │         │ · 本地存储   │         │ · 本地存储  │
    │ · 本地计算   │         │ · 本地计算   │         │ · 本地计算  │
    │ · 合规: 网安法 │         │ · 合规: GDPR │         │ · 合规: CCPA│
    │ · 数据不出域  │         │ · 数据不出域  │         │ · 数据不出域 │
    └─────────────┘         └─────────────┘         └──────────┘
```

### 7.2 合规要求矩阵

| 法规 | 地区 | 核心要求 | 技术实现 |
|------|------|---------|---------|
| **GDPR** | 欧盟 | 数据最小化、被遗忘权、数据可携带 | PII自动识别 + 数据主体请求API + 处理记录 |
| **CCPA** | 加州 | 消费者知情权、删除权、拒绝出售权 | 数据分类标签 + opt-out机制 |
| **网安法/个保法** | 中国 | 数据本地存储、跨境评估 | 中国区域独立部署 + 跨境审批流 |

### 7.3 数据驻留规则（global profile）

| 规则 | 说明 | 技术实现 |
|------|------|---------|
| **数据不出域** | 每个区域的数据存储和计算在本地 | 区域独立的Storage Backend (S3, 区域bucket) |
| **元数据可跨域** | 全局目录只存元数据，不存原始数据 | Metadata Backend 同步到全局PostgreSQL |
| **聚合数据可跨域** | 脱敏和聚合后的数据可跨区域共享 | 标记 `cross-region-safe`，全局API可用 |
| **原始数据需审批** | 跨区域访问原始数据需合规审批 | 审批流 + 数据访问代理强制执行 |

### 7.4 数据主体请求处理（GDPR compliance）

```
数据主体请求 (删除/导出/更正)
     │
     ▼
1. 身份验证
2. 数据定位（血缘追踪所有副本）
3. 执行请求
   ├── 删除: 级联删除/脱敏所有PII
   ├── 导出: JSON/CSV标准格式
   └── 更正: 更新所有副本
4. 验证与记录（不可篡改审计）
```

---

## 8. 威胁模型（所有profile评估）

| 威胁 | dev风险 | staging风险 | prod风险 | global风险 | 防护措施 |
|------|--------|-----------|---------|----------|---------|
| 数据泄露 | 低（本机） | 中（内网） | 高 | 高 | 加密 + 脱敏 + 访问控制 |
| 越权访问 | 无 | 低 | 中 | 中 | RBAC + ABAC + 审计 |
| 数据篡改 | 无 | 低 | 中 | 中 | 不可变存储 + 校验 |
| 内部威胁 | 无 | 低 | 中 | 中 | 审计 + 异常检测 + 最小权限 |
| 合规违规 | 无 | 无 | 中 | 高 | 自动合规检查 + 审计报告 |

**威胁的严重程度随profile升级而增加，安全防护也随profile升级而增强。这正是弹性安全框架的设计目标。**

---

## 9. profile升级安全检查清单

从较低profile升级到较高profile时，执行以下检查：

| 检查项 | dev→staging | staging→prod | prod→global |
|--------|------------|-------------|------------|
| 认证机制 | 确认SSO可用 | 确认MFA可用 | 确认跨区域联邦可用 |
| 授权策略 | 确认RBAC角色定义完整 | 确认ABAC规则就绪 | 确认数据驻留规则就绪 |
| 脱敏规则 | 确认PII识别规则覆盖 | 确认数据访问代理就绪 | 确认跨区域脱敏一致性 |
| 加密 | 确认TLS证书有效 | 确认KMS可用 | 确认HSM可用 |
| 审计 | 确认审计日志格式 | 确认不可篡改机制 | 确认跨区域聚合 |
| 合规 | - | 确认合规框架覆盖 | 确认多区域合规检查通过 |