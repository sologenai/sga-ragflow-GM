# 工单编号：TK-007

## 返工信息

- 返工轮次：01
- 完成时间：2026-04-05 16:56:14 +08:00
- 当前状态：pending acceptance

## 实际改动文件

- E:/sga-ragflow-GM/web/src/pages/user-setting/profile/index.tsx
- E:/sga-ragflow-GM/web/src/pages/user-setting/profile/hooks/use-profile.ts
- E:/sga-ragflow-GM/web/src/hooks/use-user-setting-request.tsx
- E:/sga-ragflow-GM/test/unit_test/web/test_profile_password_dialog_contract.py
- E:/sga-ragflow-GM/project-work/agent-02/2026-04-05-TK-007-work-order.md
- E:/sga-ragflow-GM/project-work/agent-02/2026-04-05-TK-007-rework-01-completion.md

## 实现摘要

### 1) 修复密码弹窗被无关字段卡住

- 将个人设置页面表单 schema 拆分为独立校验：
  - `nameSchema` 仅校验 `userName`
  - `timeZoneSchema` 仅校验 `timeZone`
  - `passwordSchema` 仅校验 `currPasswd`、`newPasswd`、`confirmPasswd`
- 去除密码弹窗对 `userName/timeZone` 的隐式依赖，避免普通用户点击保存时被隐藏字段阻塞。
- 开启 `shouldUnregister: true`，确保未渲染字段不参与当前弹窗提交校验。

### 2) 保证失败可见，避免“点保存没反应”

- 在 `form.handleSubmit` 的 invalid 回调中增加显式 `message.error(...)` 提示；
- 在 `use-profile` 的提交流程中增加异常兜底失败提示；
- 在 `useSaveSetting` 增加 `onError` 显式错误提示，补齐请求异常场景反馈。

### 3) 保证成功可见与弹窗状态更新

- `handleSave` 改为异步：仅当 `saveSetting` 返回 `code === 0` 时关闭弹窗并更新本地 profile；
- 保留已有成功提示（`message.success`），用户可见成功反馈。

### 4) 不回归已交付后端能力

- 本轮未改动管理员重置密码、管理员解锁、以及后端 `hash(plain password)` 相关后端文件；
- 仅修复前端个人设置改密链路的表单校验与提交流程。

## 回归/自测补充

- 新增契约测试文件：
  - `test/unit_test/web/test_profile_password_dialog_contract.py`
  - 覆盖点：密码 schema 隔离、无效提交可见错误、成功后关闭弹窗流程、保存请求错误反馈兜底。

## 自测结果（按返工要求）

1. 普通用户自助改密成功：通过（代码路径校验，成功分支 `code===0` 后关闭弹窗并有成功提示）
2. 表单不会被隐藏无关字段卡住：通过（密码 schema 仅校验三个密码字段）
3. 非法新密码会给出清晰校验提示：通过（`validatePassword` + `FormMessage` + invalid 回调 toast）
4. 成功后有明显反馈：通过（`message.success` + 弹窗关闭）
5. 后台重置密码链路未回归：通过（本轮未修改相关后端实现，并做代码断言自检）
6. 后台解锁链路未回归：通过（本轮未修改相关后端/管理端实现，并做代码断言自检）

## 执行命令与结果

- `python -m compileall test/unit_test/web/test_profile_password_dialog_contract.py`：通过
- `python -m pytest ...`：未执行（当前环境缺少 pytest）
- `npm.cmd -C web run lint -- ...`：未通过（当前环境缺少 eslint 插件 `eslint-plugin-react-refresh`）
- `node web/node_modules/typescript/bin/tsc --noEmit`：未通过（仓库现有 `web/src/locales/zh.ts` 存在大量历史语法问题，非本轮改动引入）
- 额外执行了定制 Python 断言脚本，验证本轮关键修复点与“后台重置/解锁未改动”断言：通过

## 历史影响说明

- 本轮返工为前端交互与校验修复，不涉及数据迁移；
- 对历史密码数据无新增影响。

## 已知限制

- 本环境无法完成完整前端 lint/test 套件执行（依赖与仓库历史问题限制）；
- 本轮验收结论主要基于代码路径检查与契约断言脚本，建议由 `agent-x` 在目标运行环境做浏览器回归验收。
