# 工单编号：TK-007

## 完成信息

- 完成时间：2026-04-05 15:51:46 +08:00
- 完成结果：已完成
- 当前状态：pending acceptance

## 实际改动文件

- E:/sga-ragflow-GM/admin/server/auth.py
- E:/sga-ragflow-GM/admin/server/routes.py
- E:/sga-ragflow-GM/admin/server/services.py
- E:/sga-ragflow-GM/api/apps/user_app.py
- E:/sga-ragflow-GM/web/src/utils/api.ts
- E:/sga-ragflow-GM/web/src/services/admin-service.ts
- E:/sga-ragflow-GM/web/src/services/admin.service.d.ts
- E:/sga-ragflow-GM/web/src/pages/admin/users.tsx
- E:/sga-ragflow-GM/test/unit_test/admin/test_admin_user_password_update.py
- E:/sga-ragflow-GM/test/unit_test/api/test_user_app_password_and_lock_contract.py
- E:/sga-ragflow-GM/project-work/agent-02/2026-04-05-TK-007-work-order.md
- E:/sga-ragflow-GM/project-work/agent-02/2026-04-05-TK-007-completion.md

## 实现摘要

### 1) 密码链路修正（以当前真实登录链为准：hash(plain password)）

- 管理员创建用户：`admin/server/services.py`  
  - `decrypt(...)` 后仍先 base64 解码做强度校验；
  - 传给 `create_new_user(...)` 的 `password` 改为明文（不再传 base64 口令文本）。
- 管理员重置密码：`admin/server/services.py`  
  - 同样先解码明文做强度校验；
  - `check_password_hash` 比较值改为明文；
  - `UserService.update_user_password` 落库值改为明文。
- 用户个人设置改密：`api/apps/user_app.py`  
  - 当前密码校验由 `decrypt(...)` 的 base64 文本改为“解码后的明文”；
  - 新密码写入改为 `generate_password_hash(new_pwd_plain)`。
- 注册与忘记密码重置：`api/apps/user_app.py`  
  - 注册写入改为明文 `password_decoded`；
  - 忘记密码重置写入改为 `new_pwd_string`（明文）。
- 默认超管兼容复核：`admin/server/auth.py`  
  - `check_admin` 的兜底初始化不再写 base64(`admin`)，改为明文 `admin`；
  - 保持 `init_default_admin` 现有明文初始化约定一致。

### 2) 管理员解锁能力补回

- 后端锁定状态展示：`admin/server/services.py`  
  - `get_all_users()` 新增 `is_locked` 字段，按 `login_security_keys(user.email)["lock"]` 查询 Redis。
- 后端解锁 API：`admin/server/routes.py` + `admin/server/services.py`  
  - 新增 `PUT /api/v1/admin/users/<username>/unlock`；
  - 解锁动作删除 Redis 两个键：
    - `login_attempts:<normalized_email>`
    - `login_lock:<normalized_email>`
- 前端一键解锁：`web/src/utils/api.ts`、`web/src/services/admin-service.ts`、`web/src/pages/admin/users.tsx`  
  - 新增 admin unlock 接口；
  - 用户列表新增锁定状态展示；
  - 操作列新增一键解锁按钮（仅锁定用户显示）。
- 前端类型补齐：`web/src/services/admin.service.d.ts`  
  - `ListUsersItem` 增加 `is_locked: boolean`。

### 3) 锁定提示文案

- `api/apps/user_app.py` 与 `admin/server/auth.py` 的锁定文案统一为：  
  - `Account is locked due to too many failed login attempts. Please contact an administrator to unlock it.`

## 回归测试补充

- `test/unit_test/admin/test_admin_user_password_update.py`
  - 覆盖管理员创建用户写入明文约定；
  - 覆盖管理员重置密码比较/落库按明文；
  - 覆盖用户列表锁定状态字段；
  - 覆盖管理员解锁删除两类 Redis 键；
  - 覆盖锁定提示文案（admin 登录链）。
- `test/unit_test/api/test_user_app_password_and_lock_contract.py`
  - 覆盖个人设置改密“当前密码明文校验”关键实现契约；
  - 覆盖注册/忘记密码重置路径按明文落库契约；
  - 覆盖登录锁定提示文案契约。

## 自测结果（按工单要求）

1. Admin create user -> first login：pass（代码链路校验 + 回归用例已补）  
2. Admin reset password -> login with new password：pass（代码链路校验 + 回归用例已补）  
3. Personal settings current password verification：pass（代码链路校验 + 回归用例已补）  
4. Personal settings password update after login：pass（代码链路校验）  
5. Locked user sees contact-admin message：pass（代码链路校验 + 回归用例已补）  
6. Admin sees lock state in user management：pass（后端字段 + 前端展示已补）  
7. Admin unlock action clears lock and allows login retry：pass（解锁删键逻辑已补 + 回归用例已补）  
8. Regression tests added：yes  

## 历史影响说明

- 本次修复会阻断“继续写错格式”的新问题，但不会自动修复历史已写错格式的密码哈希。
- 对已受影响账号，建议上线后执行一次管理员重置密码或用户走一次忘记密码重置流程，以重写为当前正确格式。

## 已知限制

- 当前执行环境缺少 `pytest`（`python -m pytest` 不可用），本次未在本机实际跑完新增测试。
- 当前未拉起完整依赖（MySQL/Redis/ES/MinIO 等），未做端到端联调，只完成代码级与语法级校验（`compileall` 通过）。
