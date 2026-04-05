# 工单编号：TK-004

## 完成信息

- 完成时间：2026-04-04 21:42:01 +08:00
- 完成结果：已完成
- 当前状态：待验收

## 实际改动文件

- E:/sga-ragflow-GM/admin/server/services.py
- E:/sga-ragflow-GM/test/unit_test/admin/test_admin_user_password_update.py
- E:/sga-ragflow-GM/project-work/agent-002/2026-04-04-TK-004-work-order.md
- E:/sga-ragflow-GM/project-work/agent-002/2026-04-04-TK-004-completion.md

## 实现说明

- 根因：`admin/server/services.py` 的 `UserMgr.update_user_password` 在管理员改密时，先将 `decrypt` 结果解码为明文后，错误地使用明文进行哈希比较和落库，导致密码存储格式与系统其余链路约定不一致。
- 修复点：在 `UserMgr.update_user_password` 中保留明文仅用于 `validate_password` 强度校验；哈希比较与 `UserService.update_user_password` 落库统一使用 `psw_base64`。
- 兼容性说明：
  - 与个人设置改密链路兼容：`api/apps/user_app.py` 的个人设置旧密码校验使用 `check_password_hash(current_user.password, decrypt(...))`，即按 base64 口令校验；本次修复后管理员改密写入格式与其一致。
  - 与忘记密码重置链路兼容：`forget_reset_password` 使用 `UserService.update_user_password(user.id, new_pwd_base64)`，与本次修复后的管理员改密格式一致。
  - 未改动前端加密协议与全局密码体系约定。
- 回归测试：新增 `test/unit_test/admin/test_admin_user_password_update.py`，覆盖以下回归点：
  - 密码强度校验仍使用解码后的明文。
  - 哈希比较必须使用 base64 口令。
  - 密码更新落库必须使用 base64 口令。
  - 相同密码（base64 口令一致）时不应更新。

## 自测结果

- 管理员改密路径：通过（代码路径校验）
- 新密码登录：通过（链路格式一致性校验）
- 管理员改密后个人设置再改密：通过（链路格式一致性校验）
- 注册/登录回归：未执行（当前环境缺少 `pytest` 与完整依赖服务）
- 忘记密码回归：未执行（当前环境缺少 `pytest` 与完整依赖服务）
- 回归测试补充：已补充（新增单元回归测试）

## 历史影响说明

- 历史已受影响账号是否自动修复：否
- 运维建议：
  - 对历史可能被管理员通过旧缺陷链路改过密的账号，需在修复版本上线后执行一次管理员重置密码或走一次忘记密码重置流程，以重写为正确存储格式。

## 已知限制

- 当前执行环境缺少 `pytest`（`python -m pytest` 不可用），未能本地实际运行新增测试。
- 当前未启动 MySQL/Redis/ES/MinIO 等完整依赖服务，未进行接口级端到端验测。

## 验收请求

- 请 `agent-x` 按 TK-004 工单验收标准执行联调验收。
