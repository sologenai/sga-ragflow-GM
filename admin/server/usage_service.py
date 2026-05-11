#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from io import BytesIO
from typing import Any

from api.db.db_models import API4Conversation, DB, Dialog, Knowledgebase, User, UserCanvas


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _format_datetime(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def _parse_date(value: str | None, end_of_day: bool = False) -> datetime | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None

    formats = ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d", "%Y/%m/%d %H:%M:%S")
    for fmt in formats:
        try:
            parsed = datetime.strptime(value[:19], fmt)
            if end_of_day and fmt in {"%Y-%m-%d", "%Y/%m/%d"}:
                return datetime.combine(parsed.date(), time.max)
            return parsed
        except ValueError:
            continue

    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if end_of_day and "T" not in value and len(value) <= 10:
            return datetime.combine(parsed.date(), time.max)
        return parsed.replace(tzinfo=None)
    except ValueError:
        return None


def _bucket_key(value: datetime | None, granularity: str) -> str:
    if not value:
        return "unknown"
    if granularity == "month":
        return value.strftime("%Y-%m")
    if granularity == "week":
        year, week, _ = value.isocalendar()
        return f"{year}-W{week:02d}"
    return value.strftime("%Y-%m-%d")


def _extract_question(message: Any, fallback: str | None = "") -> str:
    if isinstance(message, str):
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            return message[:200]
    if isinstance(message, list):
        for item in message:
            if not isinstance(item, dict):
                continue
            if item.get("role") in {"user", "human"}:
                content = item.get("content") or ""
                return str(content)[:200]
    if isinstance(message, dict):
        content = message.get("content") or message.get("question")
        if content:
            return str(content)[:200]
    return str(fallback or "")[:200]


@dataclass
class _Filters:
    from_date: datetime | None
    to_date: datetime | None
    source: str
    keyword: str
    user_id: str
    granularity: str


class AgentUsageMgr:
    DEFAULT_SECTIONS = ("overview", "detail", "by_app", "by_user", "chat_graphs")

    @classmethod
    def _parse_filters(cls, params: dict[str, Any]) -> _Filters:
        scope = str(params.get("scope") or "current")
        ignore_time = scope == "all"
        granularity = str(params.get("granularity") or "day")
        if granularity not in {"day", "week", "month"}:
            granularity = "day"
        source = str(params.get("source") or "all")
        if source not in {"all", "agent", "dialog"}:
            source = "all"

        return _Filters(
            from_date=None if ignore_time else _parse_date(params.get("from_date")),
            to_date=None if ignore_time else _parse_date(params.get("to_date"), end_of_day=True),
            source=source,
            keyword=str(params.get("keyword") or "").strip().lower(),
            user_id=str(params.get("user_id") or "").strip().lower(),
            granularity=granularity,
        )

    @classmethod
    def _row_to_dict(cls, row: API4Conversation, user_map: dict[str, dict[str, str]], canvas_map: dict[str, str], dialog_map: dict[str, str]) -> dict[str, Any]:
        source = row.source or ""
        app_type = "智能体" if source == "agent" else "聊天"
        if source == "agent":
            app_name = canvas_map.get(row.dialog_id) or row.name or row.dialog_id
        else:
            app_name = dialog_map.get(row.dialog_id) or row.name or row.dialog_id

        raw_user = row.user_id or row.exp_user_id or ""
        user = user_map.get(raw_user.lower(), {})
        user_name = user.get("nickname") or user.get("email") or raw_user or "-"
        user_email = user.get("email") or ""
        create_date = row.create_date
        if not isinstance(create_date, datetime):
            create_date = None

        return {
            "id": row.id,
            "app_id": row.dialog_id,
            "app_name": app_name,
            "app_type": app_type,
            "source": source or "dialog",
            "user_id": raw_user,
            "user_name": user_name,
            "user_email": user_email,
            "question": _extract_question(row.message, row.name),
            "status": "失败" if row.errors else "成功",
            "rounds": _safe_int(row.round),
            "tokens": _safe_int(row.tokens),
            "duration": round(_safe_float(row.duration), 3),
            "errors": row.errors or "",
            "create_date": _format_datetime(row.create_date),
            "_create_date_obj": create_date,
        }

    @classmethod
    def _load_user_map(cls) -> dict[str, dict[str, str]]:
        user_map: dict[str, dict[str, str]] = {}
        for user in User.select(User.id, User.nickname, User.email):
            payload = {
                "id": user.id or "",
                "nickname": user.nickname or "",
                "email": user.email or "",
            }
            if user.id:
                user_map[user.id.lower()] = payload
            if user.email:
                user_map[user.email.lower()] = payload
            if user.nickname:
                user_map[user.nickname.lower()] = payload
        return user_map

    @classmethod
    def _load_app_maps(cls) -> tuple[dict[str, str], dict[str, str]]:
        canvas_map = {row.id: row.title or row.id for row in UserCanvas.select(UserCanvas.id, UserCanvas.title)}
        dialog_map = {row.id: row.name or row.id for row in Dialog.select(Dialog.id, Dialog.name)}
        return canvas_map, dialog_map

    @classmethod
    def _load_usage_rows(cls, filters: _Filters) -> list[dict[str, Any]]:
        conditions = []
        if filters.source in {"agent", "dialog"}:
            conditions.append(API4Conversation.source == filters.source)
        else:
            conditions.append(API4Conversation.source.in_(["agent", "dialog"]))
        if filters.from_date:
            conditions.append(API4Conversation.create_date >= filters.from_date)
        if filters.to_date:
            conditions.append(API4Conversation.create_date <= filters.to_date)

        query = API4Conversation.select(
            API4Conversation.id,
            API4Conversation.name,
            API4Conversation.dialog_id,
            API4Conversation.user_id,
            API4Conversation.exp_user_id,
            API4Conversation.message,
            API4Conversation.tokens,
            API4Conversation.source,
            API4Conversation.duration,
            API4Conversation.round,
            API4Conversation.errors,
            API4Conversation.create_date,
        )
        if conditions:
            query = query.where(*conditions)
        query = query.order_by(API4Conversation.create_date.desc())

        user_map = cls._load_user_map()
        canvas_map, dialog_map = cls._load_app_maps()
        rows = [cls._row_to_dict(row, user_map, canvas_map, dialog_map) for row in query]
        return cls._filter_rows(rows, filters)

    @classmethod
    def _filter_rows(cls, rows: list[dict[str, Any]], filters: _Filters) -> list[dict[str, Any]]:
        if not filters.keyword and not filters.user_id:
            return rows
        result = []
        for row in rows:
            keyword_blob = " ".join(
                str(row.get(key) or "")
                for key in ("id", "app_id", "app_name", "app_type", "user_id", "user_name", "user_email", "question", "errors")
            ).lower()
            user_blob = " ".join(str(row.get(key) or "") for key in ("user_id", "user_name", "user_email")).lower()
            if filters.keyword and filters.keyword not in keyword_blob:
                continue
            if filters.user_id and filters.user_id not in user_blob:
                continue
            result.append(row)
        return result

    @classmethod
    def _load_chat_graphs(cls, filters: _Filters) -> list[dict[str, Any]]:
        conditions = [Knowledgebase.kb_label == "chat_graph"]
        if filters.from_date:
            conditions.append(Knowledgebase.create_date >= filters.from_date)
        if filters.to_date:
            conditions.append(Knowledgebase.create_date <= filters.to_date)

        user_map = cls._load_user_map()
        rows = []
        query = (
            Knowledgebase.select(
                Knowledgebase.id,
                Knowledgebase.name,
                Knowledgebase.created_by,
                Knowledgebase.doc_num,
                Knowledgebase.token_num,
                Knowledgebase.chunk_num,
                Knowledgebase.create_date,
            )
            .where(*conditions)
            .order_by(Knowledgebase.create_date.desc())
        )
        for kb in query:
            user = user_map.get((kb.created_by or "").lower(), {})
            payload = {
                "id": kb.id,
                "name": kb.name,
                "user_id": kb.created_by or "",
                "user_name": user.get("nickname") or user.get("email") or kb.created_by or "-",
                "user_email": user.get("email") or "",
                "doc_num": _safe_int(kb.doc_num),
                "chunk_num": _safe_int(kb.chunk_num),
                "token_num": _safe_int(kb.token_num),
                "create_date": _format_datetime(kb.create_date),
                "_create_date_obj": kb.create_date if isinstance(kb.create_date, datetime) else None,
            }
            rows.append(payload)

        if not filters.keyword and not filters.user_id:
            return rows

        result = []
        for row in rows:
            keyword_blob = " ".join(str(row.get(key) or "") for key in ("id", "name", "user_id", "user_name", "user_email")).lower()
            user_blob = " ".join(str(row.get(key) or "") for key in ("user_id", "user_name", "user_email")).lower()
            if filters.keyword and filters.keyword not in keyword_blob:
                continue
            if filters.user_id and filters.user_id not in user_blob:
                continue
            result.append(row)
        return result

    @classmethod
    def _build_overview(cls, rows: list[dict[str, Any]], chat_graphs: list[dict[str, Any]]) -> dict[str, Any]:
        total_sessions = len(rows)
        total_rounds = sum(_safe_int(row.get("rounds")) for row in rows)
        total_tokens = sum(_safe_int(row.get("tokens")) for row in rows)
        total_duration = sum(_safe_float(row.get("duration")) for row in rows)
        active_users = len({row.get("user_id") for row in rows if row.get("user_id")})
        error_count = sum(1 for row in rows if row.get("errors"))
        agent_sessions = sum(1 for row in rows if row.get("source") == "agent")
        dialog_sessions = sum(1 for row in rows if row.get("source") == "dialog")
        return {
            "total_sessions": total_sessions,
            "total_rounds": total_rounds,
            "active_users": active_users,
            "total_tokens": total_tokens,
            "total_duration": round(total_duration, 3),
            "avg_duration": round(total_duration / total_sessions, 3) if total_sessions else 0,
            "error_count": error_count,
            "agent_sessions": agent_sessions,
            "dialog_sessions": dialog_sessions,
            "chat_graph_count": len(chat_graphs),
        }

    @classmethod
    def _build_trend(cls, rows: list[dict[str, Any]], chat_graphs: list[dict[str, Any]], granularity: str) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"date": "", "sessions": 0, "rounds": 0, "tokens": 0, "errors": 0, "chat_graphs": 0}
        )
        for row in rows:
            key = _bucket_key(row.get("_create_date_obj"), granularity)
            buckets[key]["date"] = key
            buckets[key]["sessions"] += 1
            buckets[key]["rounds"] += _safe_int(row.get("rounds"))
            buckets[key]["tokens"] += _safe_int(row.get("tokens"))
            buckets[key]["errors"] += 1 if row.get("errors") else 0
        for graph in chat_graphs:
            key = _bucket_key(graph.get("_create_date_obj"), granularity)
            buckets[key]["date"] = key
            buckets[key]["chat_graphs"] += 1
        return [buckets[key] for key in sorted(buckets.keys())]

    @classmethod
    def _build_by_app(cls, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str], dict[str, Any]] = {}
        users: dict[tuple[str, str], set[str]] = defaultdict(set)
        for row in rows:
            key = (row.get("source") or "", row.get("app_id") or "")
            if key not in groups:
                groups[key] = {
                    "app_id": row.get("app_id") or "",
                    "app_name": row.get("app_name") or "-",
                    "app_type": row.get("app_type") or "-",
                    "source": row.get("source") or "",
                    "total_sessions": 0,
                    "total_rounds": 0,
                    "active_users": 0,
                    "total_tokens": 0,
                    "total_duration": 0.0,
                    "avg_duration": 0.0,
                    "error_count": 0,
                    "latest_time": "",
                }
            item = groups[key]
            item["total_sessions"] += 1
            item["total_rounds"] += _safe_int(row.get("rounds"))
            item["total_tokens"] += _safe_int(row.get("tokens"))
            item["total_duration"] += _safe_float(row.get("duration"))
            item["error_count"] += 1 if row.get("errors") else 0
            item["latest_time"] = max(item["latest_time"], row.get("create_date") or "")
            if row.get("user_id"):
                users[key].add(row["user_id"])

        for key, item in groups.items():
            item["active_users"] = len(users[key])
            item["total_duration"] = round(item["total_duration"], 3)
            item["avg_duration"] = round(item["total_duration"] / item["total_sessions"], 3) if item["total_sessions"] else 0
        return sorted(groups.values(), key=lambda item: (item["total_sessions"], item["total_rounds"]), reverse=True)

    @classmethod
    def _build_by_user(cls, rows: list[dict[str, Any]], chat_graphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        groups: dict[str, dict[str, Any]] = {}
        apps: dict[str, set[str]] = defaultdict(set)
        graph_counts: dict[str, int] = defaultdict(int)
        for graph in chat_graphs:
            user_id = graph.get("user_id") or ""
            if user_id:
                graph_counts[user_id] += 1

        for row in rows:
            key = row.get("user_id") or "-"
            if key not in groups:
                groups[key] = {
                    "user_id": key,
                    "user_name": row.get("user_name") or "-",
                    "user_email": row.get("user_email") or "",
                    "total_sessions": 0,
                    "used_apps": 0,
                    "total_rounds": 0,
                    "total_tokens": 0,
                    "total_duration": 0.0,
                    "avg_duration": 0.0,
                    "error_count": 0,
                    "chat_graph_count": graph_counts.get(key, 0),
                    "latest_time": "",
                }
            item = groups[key]
            item["total_sessions"] += 1
            item["total_rounds"] += _safe_int(row.get("rounds"))
            item["total_tokens"] += _safe_int(row.get("tokens"))
            item["total_duration"] += _safe_float(row.get("duration"))
            item["error_count"] += 1 if row.get("errors") else 0
            item["latest_time"] = max(item["latest_time"], row.get("create_date") or "")
            apps[key].add(row.get("app_id") or "")

        for key, count in graph_counts.items():
            if key not in groups:
                graph = next((item for item in chat_graphs if item.get("user_id") == key), {})
                groups[key] = {
                    "user_id": key,
                    "user_name": graph.get("user_name") or "-",
                    "user_email": graph.get("user_email") or "",
                    "total_sessions": 0,
                    "used_apps": 0,
                    "total_rounds": 0,
                    "total_tokens": 0,
                    "total_duration": 0.0,
                    "avg_duration": 0.0,
                    "error_count": 0,
                    "chat_graph_count": count,
                    "latest_time": graph.get("create_date") or "",
                }

        for key, item in groups.items():
            item["used_apps"] = len([app for app in apps[key] if app])
            item["total_duration"] = round(item["total_duration"], 3)
            item["avg_duration"] = round(item["total_duration"] / item["total_sessions"], 3) if item["total_sessions"] else 0
        return sorted(groups.values(), key=lambda item: (item["total_sessions"], item["chat_graph_count"]), reverse=True)

    @classmethod
    @DB.connection_context()
    def get_summary(cls, params: dict[str, Any]) -> dict[str, Any]:
        filters = cls._parse_filters(params)
        rows = cls._load_usage_rows(filters)
        chat_graphs = cls._load_chat_graphs(filters)
        clean_detail = [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows[:200]]
        return {
            "overview": cls._build_overview(rows, chat_graphs),
            "trend": cls._build_trend(rows, chat_graphs, filters.granularity),
            "by_app": cls._build_by_app(rows)[:50],
            "by_user": cls._build_by_user(rows, chat_graphs)[:50],
            "chat_graphs": [{k: v for k, v in row.items() if not k.startswith("_")} for row in chat_graphs[:100]],
            "detail": clean_detail,
            "total_detail": len(rows),
            "filters": {
                "from_date": _format_datetime(filters.from_date),
                "to_date": _format_datetime(filters.to_date),
                "source": filters.source,
                "granularity": filters.granularity,
            },
        }

    @classmethod
    def _append_sheet(cls, workbook, title: str, headers: list[tuple[str, str]], rows: list[dict[str, Any]]):
        sheet = workbook.create_sheet(title=title)
        sheet.append([label for _, label in headers])
        for cell in sheet[1]:
            cell.font = cell.font.copy(bold=True)
            cell.fill = cell.fill.copy(fgColor="E6F4FF", fill_type="solid")
        for row in rows:
            sheet.append([row.get(key, "") for key, _ in headers])
        for column in sheet.columns:
            max_length = max(len(str(cell.value or "")) for cell in column)
            sheet.column_dimensions[column[0].column_letter].width = min(max(max_length + 2, 12), 48)
        sheet.freeze_panes = "A2"

    @classmethod
    @DB.connection_context()
    def build_export(cls, params: dict[str, Any]) -> tuple[bytes, str]:
        from openpyxl import Workbook

        filters = cls._parse_filters(params)
        rows = cls._load_usage_rows(filters)
        chat_graphs = cls._load_chat_graphs(filters)
        summary = cls._build_overview(rows, chat_graphs)
        trend = cls._build_trend(rows, chat_graphs, filters.granularity)
        by_app = cls._build_by_app(rows)
        by_user = cls._build_by_user(rows, chat_graphs)

        sections_param = str(params.get("sections") or "all")
        sections = [item.strip() for item in sections_param.split(",") if item.strip()]
        if not sections or "all" in sections:
            sections = list(cls.DEFAULT_SECTIONS)

        workbook = Workbook()
        workbook.remove(workbook.active)

        if "overview" in sections:
            overview_rows = [{"metric": key, "value": value} for key, value in summary.items()]
            cls._append_sheet(workbook, "总览", [("metric", "指标"), ("value", "数值")], overview_rows)

        if "trend" in sections:
            cls._append_sheet(
                workbook,
                "趋势",
                [
                    ("date", "时间"),
                    ("sessions", "会话数"),
                    ("rounds", "对话轮数"),
                    ("tokens", "Token"),
                    ("errors", "失败数"),
                    ("chat_graphs", "聊天图谱生成数"),
                ],
                trend,
            )

        if "by_app" in sections:
            cls._append_sheet(
                workbook,
                "按智能体和聊天",
                [
                    ("app_name", "名称"),
                    ("app_type", "类型"),
                    ("app_id", "ID"),
                    ("total_sessions", "会话数"),
                    ("total_rounds", "对话轮数"),
                    ("active_users", "活跃用户"),
                    ("total_tokens", "Token"),
                    ("avg_duration", "平均耗时"),
                    ("error_count", "失败数"),
                    ("latest_time", "最近调用"),
                ],
                by_app,
            )

        if "by_user" in sections:
            cls._append_sheet(
                workbook,
                "按用户",
                [
                    ("user_name", "用户"),
                    ("user_email", "邮箱"),
                    ("user_id", "用户ID"),
                    ("total_sessions", "会话数"),
                    ("total_rounds", "对话轮数"),
                    ("used_apps", "使用应用数"),
                    ("chat_graph_count", "聊天图谱生成数"),
                    ("total_tokens", "Token"),
                    ("avg_duration", "平均耗时"),
                    ("error_count", "失败数"),
                    ("latest_time", "最近调用"),
                ],
                by_user,
            )

        if "chat_graphs" in sections:
            graph_rows = [{k: v for k, v in row.items() if not k.startswith("_")} for row in chat_graphs]
            cls._append_sheet(
                workbook,
                "聊天图谱",
                [
                    ("name", "知识库名称"),
                    ("id", "知识库ID"),
                    ("user_name", "用户"),
                    ("user_email", "邮箱"),
                    ("user_id", "用户ID"),
                    ("doc_num", "文件数"),
                    ("chunk_num", "分块数"),
                    ("token_num", "Token"),
                    ("create_date", "创建时间"),
                ],
                graph_rows,
            )

        if "detail" in sections:
            detail_rows = [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]
            cls._append_sheet(
                workbook,
                "调用明细",
                [
                    ("create_date", "创建时间"),
                    ("app_type", "类型"),
                    ("app_name", "名称"),
                    ("app_id", "ID"),
                    ("user_name", "用户"),
                    ("user_email", "邮箱"),
                    ("user_id", "用户ID"),
                    ("question", "问题"),
                    ("status", "状态"),
                    ("rounds", "轮数"),
                    ("tokens", "Token"),
                    ("duration", "耗时"),
                    ("errors", "错误"),
                ],
                detail_rows,
            )

        buffer = BytesIO()
        workbook.save(buffer)
        filename = f"agent_usage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return buffer.getvalue(), filename
