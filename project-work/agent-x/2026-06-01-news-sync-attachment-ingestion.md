# 2026-06-01 新闻同步附件入库解析改造记录

## 背景

用户确认 OA 内网新闻接口的 `mainTable.attachments` 字段会返回正文图片和附件 ID。

附件下载方式：

```text
http://oa.itg.cn/weaver/file/ItgFileDownload?fileid=附件id
```

该下载地址免鉴权。

## 本次改动

文件：`api/db/services/news_sync_service.py`

新增能力：

1. 从 `mainTable.attachments` 抽取附件 ID。
2. 从新闻正文 HTML 里的 `ItgFileDownload?fileid=...` 兜底抽取图片/附件 ID。
3. 对附件 ID 去重，避免同一条新闻重复下载。
4. 按附件 ID 下载文件，支持 `Content-Disposition` 文件名和 `Content-Type` 后缀推断。
5. 下载成功后上传到对应年份新闻知识库。
6. 上传成功后设置解析器并调用 `DocumentService.run()` 进入解析队列。
7. 如果正文文件已存在，仍会继续处理附件，支持对历史已同步正文补附件。

## 解析方式规则

本需求只针对图片和普通文件，不扩展其它媒体类型解析方式。

| 类型 | 后缀示例 | parser_id | 说明 |
| --- | --- | --- | --- |
| 新闻正文 HTML | `.html` | `naive` | 正文是通用 HTML/文本，按 General 方式解析。 |
| 图片 | `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.tif` | `picture` | 正文图片和图片附件走图片解析。 |
| 普通文件 | `.pdf`, `.doc`, `.docx`, `.txt`, `.md`, `.html`, `.rtf`, `.wps`, `.xls`, `.xlsx`, `.csv`, `.ppt`, `.pptx` 等 | `naive` | 文件附件统一按 General/naive 解析，避免引入页面不可见或不确定的专用解析配置。 |
| 非图片非文件 | 未知后缀、无后缀且无法通过 `Content-Type` 判断、其它不符合图片或普通文件后缀的内容 | 跳过 | 避免把不适合的二进制内容或错误页入库。 |

## 运行参数

可通过环境变量调整：

```text
NEWS_ATTACHMENT_DOWNLOAD_URL=http://oa.itg.cn/weaver/file/ItgFileDownload?fileid={fileid}
NEWS_ATTACHMENT_DOWNLOAD_TIMEOUT=60
NEWS_ATTACHMENT_MAX_BYTES=104857600
```

## 验证

已完成：

```text
python -m py_compile api\db\services\news_sync_service.py
```

本地无法直接完成真实 OA 下载联调：当前环境不在内网，OA 接口需要在远端环境验证。

远端复测建议：

1. 找一条 `attachments` 非空的新闻日期。
2. 后台手动触发该日期新闻同步。
3. 查看对应年份新闻知识库是否出现正文 HTML 和附件文件。
4. 检查图片附件的解析列是否进入运行/完成状态。
5. 检查普通文件附件是否按 General/naive 方式解析。
6. 用附件中的关键词做检索测试。
