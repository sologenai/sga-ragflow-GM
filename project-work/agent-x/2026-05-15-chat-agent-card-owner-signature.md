# 聊天和智能体卡片创建人署名补齐

时间：2026-05-15 19:11:15

## 背景

国贸环境中，知识库卡片可以看到创建账户署名，但聊天卡片和部分智能体入口没有统一显示创建账户。项目经理要求补齐，便于多账号协作时快速判断资源归属。

## 结论

- 后端列表接口已经具备创建人昵称来源：
  - 聊天列表 `DialogService.get_by_tenant_ids` 已联表返回 `User.nickname`。
  - 智能体列表 `UserCanvasService.get_by_tenant_ids` / `get_all_canvas` 已联表返回 `User.nickname`。
- 本次主要修正前端展示缺口，不改数据结构和权限逻辑。

## 改动范围

- `web/src/components/shared-badge.tsx`
  - 署名组件不再隐藏当前登录用户，保证“哪个账户创建就显示哪个账户署名”。
- `web/src/pages/next-chats/chat-card.tsx`
  - 聊天列表卡片显示 `data.nickname`。
- `web/src/pages/home/chat-list.tsx`
  - 首页聊天卡片显示 `x.nickname`。
- `web/src/pages/home/agent-list.tsx`
  - 首页智能体卡片显示 `x.nickname`。
- `web/src/interfaces/database/chat.ts`
  - 补充聊天列表接口返回的 `nickname`、`tenant_avatar`、`operator_permission` 类型声明。

## 验收要点

- 知识库、聊天、智能体卡片底部右侧都能显示创建账户署名。
- 当前登录用户创建的资源也显示署名，不再被前端隐藏。
- 不影响已有聊天、智能体、知识库的列表查询和点击进入逻辑。
