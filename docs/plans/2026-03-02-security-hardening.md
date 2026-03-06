# 国贸安全加固 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 满足厦门国贸安全部门反馈的全部安全要求（排除三权分立和权限隔离）

**Architecture:** 在现有 Flask-Login + Redis Session 架构上增强：(1) 后端新增密码校验工具、登录安全控制、审计日志系统；(2) 前端新增密码强度提示、空闲超时检测、客户端信息采集。所有安全状态通过 Redis 管理，审计日志存入新建的 `audit_log` 数据库表。

**Tech Stack:** Python/Quart 后端, Peewee ORM, Redis (Valkey), React/TypeScript 前端, Zod 校验, Nginx TLS

---

## Batch 1: 后端安全基础设施（Codex — 可并行开发）

### Task 1: 强密码校验工具

**Files:**
- Create: `api/utils/password_validation.py`
- Modify: `api/apps/user_app.py` (注册、改密、重置密码入口)
- Modify: `admin/server/routes.py` (管理员创建用户、改密入口)

**密码规则（国贸要求）:**
1. 至少 8 位
2. 大写字母、小写字母、数字、特殊字符 — 至少包含 3 种
3. 不能包含 4 个及以上连续数字或字母（升序/降序，如 1234, abcd, DCBA）
4. 不能包含账号（如账号是 ace，密码不能包含连续的 ace）

**Step 1: 创建密码校验模块**

```python
# api/utils/password_validation.py
import re
from typing import Optional


def validate_password(password: str, account: str = "") -> Optional[str]:
    """
    校验密码强度，返回 None 表示通过，返回字符串为错误信息。
    """
    # 规则1: 至少8位
    if len(password) < 8:
        return "Password must be at least 8 characters long"

    # 规则2: 至少包含3种字符类型
    type_count = 0
    if re.search(r'[A-Z]', password):
        type_count += 1
    if re.search(r'[a-z]', password):
        type_count += 1
    if re.search(r'[0-9]', password):
        type_count += 1
    if re.search(r'[^A-Za-z0-9]', password):
        type_count += 1
    if type_count < 3:
        return "Password must contain at least 3 of: uppercase, lowercase, digits, special characters"

    # 规则3: 不能包含4个及以上连续字符
    if _has_consecutive_sequence(password, 4):
        return "Password must not contain 4 or more consecutive characters (e.g., 1234, abcd, DCBA)"

    # 规则4: 不能包含账号
    if account and len(account) >= 3 and account.lower() in password.lower():
        return f"Password must not contain the account name"

    return None


def _has_consecutive_sequence(s: str, min_len: int) -> bool:
    """检测是否包含 min_len 个及以上的连续升序或降序字符"""
    if len(s) < min_len:
        return False

    lower = s.lower()

    for i in range(len(lower) - min_len + 1):
        # 检查升序
        is_ascending = True
        is_descending = True
        for j in range(1, min_len):
            if ord(lower[i + j]) != ord(lower[i + j - 1]) + 1:
                is_ascending = False
            if ord(lower[i + j]) != ord(lower[i + j - 1]) - 1:
                is_descending = False
            if not is_ascending and not is_descending:
                break
        if is_ascending or is_descending:
            return True

    return False
```

**Step 2: 在用户注册入口增加后端校验**

文件 `api/apps/user_app.py`，在 `user_add` 函数（约 line 735 左右，密码解密之后）插入：

```python
from api.utils.password_validation import validate_password

# 在 password 解密后、hash 之前:
pwd_error = validate_password(password_plaintext, email)
if pwd_error:
    return get_error_data_result(message=pwd_error)
```

同样应用于：
- `setting_user` 函数（约 line 550，密码更新逻辑处）
- `forget_reset_password` 函数（约 line 1040，密码重置处）
- `admin/server/routes.py` 的创建用户（约 line 95）和改密路由（约 line 140）

**Step 3: Commit**

```
feat: 添加后端强密码校验工具并应用到所有密码入口
```

---

### Task 2: 审计日志模型 + 服务

**Files:**
- Modify: `api/db/db_models.py` (新增 AuditLog 模型 + 迁移)
- Create: `api/db/services/audit_log_service.py`
- Modify: `api/db/__init__.py` (新增审计动作枚举)

**Step 1: 新增审计动作枚举**

在 `api/db/__init__.py` 末尾添加：

```python
class AuditActionType(StrEnum):
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    ACCOUNT_LOCKED = "account_locked"
    SESSION_EXPIRED = "session_expired"
    SESSION_KICKED = "session_kicked"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"
    USER_ACTIVATED = "user_activated"
    USER_DEACTIVATED = "user_deactivated"
    PASSWORD_CHANGED = "password_changed"
    PASSWORD_RESET = "password_reset"
    ADMIN_GRANTED = "admin_granted"
    ADMIN_REVOKED = "admin_revoked"
    SETTINGS_UPDATED = "settings_updated"
    KB_CREATED = "kb_created"
    KB_DELETED = "kb_deleted"
    KB_UPDATED = "kb_updated"
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_DELETED = "document_deleted"
    LOG_CLEARED = "log_cleared"
```

**Step 2: 新增 AuditLog 数据库模型**

在 `api/db/db_models.py`，在 `SystemSettings` 类之后添加：

```python
class AuditLog(DataBaseModel):
    id = CharField(max_length=32, primary_key=True)
    user_id = CharField(max_length=32, null=True, index=True)
    user_email = CharField(max_length=255, null=True, index=True)
    action_type = CharField(max_length=64, index=True)
    resource_type = CharField(max_length=64, null=True, index=True)
    resource_id = CharField(max_length=255, null=True)
    detail = LongTextField(null=True)  # JSON: {"old": {...}, "new": {...}, "description": "..."}
    ip_address = CharField(max_length=128, null=True)
    user_agent = CharField(max_length=512, null=True)
    client_info = TextField(null=True)  # JSON: {"hostname": "...", "mac": "..."}
    create_time = DateTimeField(null=True, index=True)

    class Meta:
        db_table = "audit_log"
```

此模型会被 `init_database_tables()` 自动识别并建表（Peewee introspection 机制）。

**Step 3: 新增审计日志服务**

```python
# api/db/services/audit_log_service.py
import json
from datetime import datetime

from api.db import AuditActionType
from api.db.db_models import AuditLog, DB
from api.db.services.common_service import CommonService
from api.utils import get_uuid


class AuditLogService(CommonService):
    model = AuditLog

    @classmethod
    @DB.connection_context()
    def log(cls, action_type: str, user_id: str = None, user_email: str = None,
            resource_type: str = None, resource_id: str = None,
            detail: dict = None, ip_address: str = None,
            user_agent: str = None, client_info: dict = None):
        return cls.model.create(
            id=get_uuid(),
            user_id=user_id,
            user_email=user_email,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            ip_address=ip_address,
            user_agent=user_agent,
            client_info=json.dumps(client_info, ensure_ascii=False) if client_info else None,
            create_time=datetime.now(),
        )

    @classmethod
    @DB.connection_context()
    def query_logs(cls, page=1, page_size=20, action_type=None,
                   user_email=None, date_from=None, date_to=None,
                   order_by="create_time", desc=True):
        query = cls.model.select()
        if action_type:
            query = query.where(cls.model.action_type == action_type)
        if user_email:
            query = query.where(cls.model.user_email.contains(user_email))
        if date_from:
            query = query.where(cls.model.create_time >= date_from)
        if date_to:
            query = query.where(cls.model.create_time <= date_to)

        total = query.count()
        order_field = getattr(cls.model, order_by, cls.model.create_time)
        if desc:
            order_field = order_field.desc()
        items = list(query.order_by(order_field).paginate(page, page_size).dicts())
        return items, total

    @classmethod
    @DB.connection_context()
    def cleanup_old_logs(cls, retention_days=180):
        """清理超过保留期的日志，清理前记录一条审计"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=retention_days)
        count = cls.model.select().where(cls.model.create_time < cutoff).count()
        if count > 0:
            cls.log(
                action_type=AuditActionType.LOG_CLEARED,
                detail={"description": f"Auto cleanup {count} audit logs older than {retention_days} days"},
            )
            cls.model.delete().where(cls.model.create_time < cutoff).execute()
        return count
```

**Step 4: Commit**

```
feat: 新增审计日志数据库模型和服务
```

---

### Task 3: 登录安全控制（单会话 + 失败限制 + 锁定）

**Files:**
- Modify: `api/apps/user_app.py` (login 函数)
- Modify: `api/apps/__init__.py` (_load_user 函数)
- Modify: `admin/server/auth.py` (admin login)
- Modify: `api/utils/web_utils.py` (新增登录安全常量)

**Step 1: 新增登录安全常量**

在 `api/utils/web_utils.py` 的 OTP 常量后面添加：

```python
# Login security constants
LOGIN_ATTEMPT_LIMIT = 5           # 最大登录失败次数
LOGIN_LOCK_SECONDS = 60 * 60      # 锁定时长：60分钟
LOGIN_ATTEMPT_TTL = 60 * 60       # 失败计数 TTL：60分钟
SESSION_IDLE_TIMEOUT = 60 * 60    # 会话空闲超时：60分钟


def login_security_keys(email: str):
    """生成登录安全相关的 Redis key"""
    return {
        "attempts": f"login_attempts:{email}",
        "lock": f"login_lock:{email}",
    }


def session_keys(user_id: str):
    """生成会话管理的 Redis key"""
    return {
        "active_token": f"session_active:{user_id}",
        "last_activity": f"session_activity:{user_id}",
    }
```

**Step 2: 改造用户端 login 函数 (`api/apps/user_app.py` line 66-142)**

在 login 函数中，密码校验之前增加锁定检查和失败计数；成功后增加单会话控制和审计日志：

```python
# 在 login 函数开头（email 获取之后）:
from api.utils.web_utils import login_security_keys, session_keys, LOGIN_ATTEMPT_LIMIT, LOGIN_LOCK_SECONDS, LOGIN_ATTEMPT_TTL, SESSION_IDLE_TIMEOUT
from api.db.services.audit_log_service import AuditLogService
from api.db import AuditActionType

ip_address = request.headers.get("X-Forwarded-For", request.headers.get("X-Real-Ip", request.remote_addr))
user_agent = request.headers.get("User-Agent", "")

lk = login_security_keys(email)

# 1. 检查是否被锁定
if REDIS_CONN.exist(lk["lock"]):
    AuditLogService.log(
        action_type=AuditActionType.LOGIN_FAILED,
        user_email=email,
        detail={"reason": "account_locked"},
        ip_address=ip_address, user_agent=user_agent,
    )
    return get_error_data_result(message="Account is locked due to too many failed attempts. Please try again later.")

# ... (原有的邮箱查找和密码校验逻辑) ...

# 2. 密码校验失败时（在返回密码错误之前）:
attempts = REDIS_CONN.get(lk["attempts"])
attempts = int(attempts) + 1 if attempts else 1
REDIS_CONN.set(lk["attempts"], str(attempts), LOGIN_ATTEMPT_TTL)
if attempts >= LOGIN_ATTEMPT_LIMIT:
    REDIS_CONN.set(lk["lock"], "1", LOGIN_LOCK_SECONDS)
    AuditLogService.log(
        action_type=AuditActionType.ACCOUNT_LOCKED,
        user_email=email,
        detail={"reason": f"Too many failed attempts ({attempts})", "lock_minutes": LOGIN_LOCK_SECONDS // 60},
        ip_address=ip_address, user_agent=user_agent,
    )
remaining = LOGIN_ATTEMPT_LIMIT - attempts
AuditLogService.log(
    action_type=AuditActionType.LOGIN_FAILED,
    user_email=email,
    detail={"reason": "invalid_password", "remaining_attempts": max(remaining, 0)},
    ip_address=ip_address, user_agent=user_agent,
)
# return 原有的错误响应，但消息中加入剩余次数提示

# 3. 登录成功后（生成 access_token 之后）:
# 清除失败计数
REDIS_CONN.transaction(lk["attempts"])  # 删除 key
REDIS_CONN.transaction(lk["lock"])      # 删除 key
# 注意：用 REDIS_CONN 的 delete 方法，具体看 RedisDB 接口

# 单会话控制：存储当前用户的唯一活跃 token
sk = session_keys(user.id)
old_token = REDIS_CONN.get(sk["active_token"])
if old_token:
    # 旧 session 被踢，记录审计
    AuditLogService.log(
        action_type=AuditActionType.SESSION_KICKED,
        user_id=user.id, user_email=user.email,
        detail={"reason": "new_login_from_another_location"},
        ip_address=ip_address, user_agent=user_agent,
    )
REDIS_CONN.set(sk["active_token"], user.access_token, SESSION_IDLE_TIMEOUT)
REDIS_CONN.set(sk["last_activity"], str(int(time.time())), SESSION_IDLE_TIMEOUT)

# 记录登录成功审计
AuditLogService.log(
    action_type=AuditActionType.LOGIN_SUCCESS,
    user_id=user.id, user_email=user.email,
    detail={"login_channel": "password"},
    ip_address=ip_address, user_agent=user_agent,
)
```

**Step 3: 改造 _load_user 函数 (`api/apps/__init__.py` line 95-139)**

在 token 验证通过后，增加单会话和空闲超时检查：

```python
# 在 user 查到之后、return user 之前:
from api.utils.web_utils import session_keys, SESSION_IDLE_TIMEOUT

sk = session_keys(user.id)
active_token = REDIS_CONN.get(sk["active_token"])
if active_token and active_token != access_token:
    # 此 token 不是当前活跃 token，说明被新登录踢掉了
    return None  # 返回 None 让 Flask-Login 视为未认证 → 401

# 检查空闲超时
last_activity = REDIS_CONN.get(sk["last_activity"])
if not last_activity:
    return None  # session 已过期

# 刷新活跃时间（每次认证请求都刷新）
REDIS_CONN.set(sk["active_token"], access_token, SESSION_IDLE_TIMEOUT)
REDIS_CONN.set(sk["last_activity"], str(int(time.time())), SESSION_IDLE_TIMEOUT)
```

**Step 4: 同样改造 admin login (`admin/server/auth.py` line 178-205)**

应用相同的锁定检查、失败计数、单会话控制和审计日志逻辑。

**Step 5: Commit**

```
feat: 实现单会话控制、登录失败限制和账户锁定
```

---

### Task 4: 关键操作审计埋点

**Files:**
- Modify: `admin/server/routes.py` (管理员操作：创建/删除用户、改密、激活/停用、授权)
- Modify: `api/apps/user_app.py` (用户操作：改密、登出)
- Modify: `api/apps/kb_app.py` (知识库操作：创建、删除、更新)
- Modify: `api/apps/document_app.py` (文档操作：上传、删除)

**原则：** 在每个关键操作成功执行后，调用 `AuditLogService.log()` 记录。

**Step 1: 管理员操作审计**

在 `admin/server/routes.py` 各路由处理函数中，操作成功后插入审计日志。示例（创建用户）：

```python
# POST /api/v1/admin/users 成功后:
AuditLogService.log(
    action_type=AuditActionType.USER_CREATED,
    user_id=current_user.id,
    user_email=current_user.email,
    resource_type="user",
    resource_id=new_user_email,
    detail={"created_email": new_user_email, "role": role},
    ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
    user_agent=request.headers.get("User-Agent", ""),
)
```

类似地为以下操作添加审计：
- 删除用户 → `USER_DELETED`
- 修改密码 → `PASSWORD_CHANGED`
- 激活/停用 → `USER_ACTIVATED` / `USER_DEACTIVATED`
- 授予/撤销管理员 → `ADMIN_GRANTED` / `ADMIN_REVOKED`

**Step 2: 用户操作审计**

- 登出 (`log_out` 函数) → `LOGOUT`
- 修改密码 (`setting_user` 函数) → `PASSWORD_CHANGED`
- 重置密码 (`forget_reset_password` 函数) → `PASSWORD_RESET`

**Step 3: 业务操作审计（知识库、文档）**

在 `kb_app.py` 和 `document_app.py` 的关键操作中添加审计日志：
- 创建知识库 → `KB_CREATED`
- 删除知识库 → `KB_DELETED`
- 上传文档 → `DOCUMENT_UPLOADED`
- 删除文档 → `DOCUMENT_DELETED`

**Step 4: Commit**

```
feat: 为管理员操作和关键业务操作添加审计日志
```

---

### Task 5: 审计日志 API + 日志保留策略

**Files:**
- Modify: `admin/server/routes.py` (新增审计日志查询 API)
- Create: `api/apps/audit_app.py` (或在 admin routes 中添加)

**Step 1: 新增审计日志查询 API**

在 `admin/server/routes.py` 中添加：

```python
@manager.route("/api/v1/admin/audit-logs", methods=["GET"])
@check_admin_auth
def list_audit_logs():
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 20))
    action_type = request.args.get("action_type")
    user_email = request.args.get("user_email")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    items, total = AuditLogService.query_logs(
        page=page, page_size=page_size,
        action_type=action_type, user_email=user_email,
        date_from=date_from, date_to=date_to,
    )
    return get_result(data={"items": items, "total": total})
```

**Step 2: 日志清理定时任务**

在 ragflow 启动时注册一个每天执行一次的任务，调用 `AuditLogService.cleanup_old_logs(180)` 清理超过 180 天的日志。

同时修改 `pipeline_operation_log_service.py` 的清理逻辑：将基于条数的轮转改为基于时间（180天），并在清理前记录审计日志。

**Step 3: Commit**

```
feat: 新增审计日志查询API和180天日志保留策略
```

---

### Task 6: TLS 配置加固

**Files:**
- Modify: `docker/nginx/ragflow.https.conf` (强化 TLS 配置)

**Step 1: 在 HTTPS 配置中明确限制 TLS 版本和密码套件**

```nginx
# 在 ragflow.https.conf 的 server block 中添加:
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
ssl_prefer_server_ciphers on;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;

# HSTS
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
```

**Step 2: Commit**

```
feat: 加固 Nginx TLS 配置，限制 TLSv1.2/1.3 + 安全密码套件
```

---

## Batch 2: 前端安全增强（Gemini）

### Task 7: 密码强度实时校验 UI

**Files:**
- Create: `web/src/utils/password-validation.ts`
- Modify: `web/src/pages/login-next/index.tsx` (注册表单密码校验)
- Modify: `web/src/pages/user-setting/profile/index.tsx` (改密表单)
- Modify: `web/src/pages/admin/forms/user-form.tsx` (管理员创建用户)
- Modify: `web/src/pages/admin/forms/change-password-form.tsx` (管理员改密)
- Modify: `web/src/locales/en.ts` + `web/src/locales/zh.ts` (翻译)

**Step 1: 创建前端密码校验工具**

```typescript
// web/src/utils/password-validation.ts
export interface PasswordRule {
  key: string;
  label: string;
  test: (password: string, account?: string) => boolean;
}

export const passwordRules: PasswordRule[] = [
  {
    key: 'minLength',
    label: 'password.ruleMinLength',
    test: (p) => p.length >= 8,
  },
  {
    key: 'charTypes',
    label: 'password.ruleCharTypes',
    test: (p) => {
      let count = 0;
      if (/[A-Z]/.test(p)) count++;
      if (/[a-z]/.test(p)) count++;
      if (/[0-9]/.test(p)) count++;
      if (/[^A-Za-z0-9]/.test(p)) count++;
      return count >= 3;
    },
  },
  {
    key: 'noSequential',
    label: 'password.ruleNoSequential',
    test: (p) => !hasConsecutiveSequence(p, 4),
  },
  {
    key: 'noAccount',
    label: 'password.ruleNoAccount',
    test: (p, account) =>
      !account || account.length < 3 || !p.toLowerCase().includes(account.toLowerCase()),
  },
];

function hasConsecutiveSequence(s: string, minLen: number): boolean {
  const lower = s.toLowerCase();
  for (let i = 0; i <= lower.length - minLen; i++) {
    let asc = true, desc = true;
    for (let j = 1; j < minLen; j++) {
      if (lower.charCodeAt(i + j) !== lower.charCodeAt(i + j - 1) + 1) asc = false;
      if (lower.charCodeAt(i + j) !== lower.charCodeAt(i + j - 1) - 1) desc = false;
      if (!asc && !desc) break;
    }
    if (asc || desc) return true;
  }
  return false;
}

export function validatePassword(password: string, account?: string): string | null {
  for (const rule of passwordRules) {
    if (!rule.test(password, account)) {
      return rule.label;  // 返回翻译 key
    }
  }
  return null;
}
```

**Step 2: 在各表单的 Zod schema 中使用 `superRefine` 调用 `validatePassword`**

示例（注册表单）：

```typescript
password: z.string().superRefine((val, ctx) => {
  const error = validatePassword(val, form.getValues('email'));
  if (error) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: t(error) });
  }
}),
```

**Step 3: 添加翻译文本**

在 `zh.ts` 和 `en.ts` 中添加：
```
password.ruleMinLength: "密码长度至少8位" / "At least 8 characters"
password.ruleCharTypes: "须包含大写、小写、数字、特殊字符中的至少3种" / "Must contain at least 3 of: uppercase, lowercase, digits, special characters"
password.ruleNoSequential: "不能包含4个及以上连续字符（如1234, abcd）" / "Must not contain 4+ consecutive characters (e.g., 1234, abcd)"
password.ruleNoAccount: "不能包含账号名" / "Must not contain the account name"
```

**Step 4: Commit**

```
feat: 前端密码强度实时校验和规则提示
```

---

### Task 8: 会话空闲超时前端检测

**Files:**
- Create: `web/src/hooks/use-idle-timeout.ts`
- Modify: `web/src/layouts/` 或顶层 layout 组件（挂载 idle 检测）
- Modify: `web/src/locales/en.ts` + `web/src/locales/zh.ts`

**Step 1: 创建 idle timeout hook**

```typescript
// web/src/hooks/use-idle-timeout.ts
import { useCallback, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router';
import { message } from '@/components/ui/message';
import authorizationUtil from '@/utils/authorization-util';

const IDLE_TIMEOUT = 55 * 60 * 1000; // 55分钟（略小于后端60分钟）
const ACTIVITY_EVENTS = ['mousedown', 'keydown', 'scroll', 'touchstart'];

export function useIdleTimeout() {
  const timerRef = useRef<ReturnType<typeof setTimeout>>();
  const navigate = useNavigate();

  const handleTimeout = useCallback(() => {
    authorizationUtil.removeAll();
    message.warning(t('session.expiredMessage'));
    navigate('/login');
  }, [navigate]);

  const resetTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(handleTimeout, IDLE_TIMEOUT);
  }, [handleTimeout]);

  useEffect(() => {
    ACTIVITY_EVENTS.forEach((evt) => window.addEventListener(evt, resetTimer));
    resetTimer();
    return () => {
      ACTIVITY_EVENTS.forEach((evt) => window.removeEventListener(evt, resetTimer));
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [resetTimer]);
}
```

**Step 2: 在主 layout 中挂载**

在认证后的 layout 组件中调用 `useIdleTimeout()`。

**Step 3: 处理 401 响应中的 session-kicked 场景**

在 `web/src/utils/request.ts` 和 `web/src/services/admin-service.ts` 的 401 拦截器中，增加提示消息区分"被踢下线"和"会话过期"。

**Step 4: Commit**

```
feat: 前端空闲超时检测和自动下线提示
```

---

### Task 9: 审计日志管理页面（Admin）

**Files:**
- Create: `web/src/pages/admin/audit-logs.tsx`
- Modify: `web/src/routes.tsx` (新增路由)
- Modify: `web/src/pages/admin/layouts/navigation-layout.tsx` (新增导航项)
- Modify: `web/src/services/admin-service.ts` (新增 API)
- Modify: `web/src/locales/en.ts` + `web/src/locales/zh.ts`

**Step 1: 新增审计日志页面**

展示审计日志列表，支持按时间、操作类型、用户过滤，表格显示：时间、用户、操作类型、资源、IP、详情。

**Step 2: 新增路由和导航**

在 `Routes` 枚举中添加 `AdminAuditLogs = '/admin/audit-logs'`，在路由配置和导航侧边栏中注册。

**Step 3: Commit**

```
feat: 新增审计日志管理页面
```

---

## 任务分派总览

| Task | 分配 | 依赖 | 说明 |
|------|------|------|------|
| Task 1: 强密码校验 | **Codex** | 无 | 后端工具 + 全入口集成 |
| Task 2: 审计日志模型 | **Codex** | 无 | DB模型 + Service |
| Task 3: 登录安全控制 | **Codex** | Task 2 | 单会话 + 失败限制 + 锁定 |
| Task 4: 操作审计埋点 | **Codex** | Task 2 | 管理员+业务操作审计 |
| Task 5: 审计API+保留策略 | **Codex** | Task 2 | 查询API + 180天保留 |
| Task 6: TLS 配置 | **Codex** | 无 | Nginx 加固 |
| Task 7: 密码强度 UI | **Gemini** | 无 | 前端校验 + 提示 |
| Task 8: 空闲超时检测 | **Gemini** | 无 | 前端 idle hook |
| Task 9: 审计日志页面 | **Gemini** | Task 5 | Admin 管理页面 |

**并行策略：**
- Codex: Task 1 + Task 2 可并行 → Task 3/4/5 串行（依赖 Task 2）→ Task 6
- Gemini: Task 7 + Task 8 可并行 → Task 9（等 Task 5 API 就绪后）
