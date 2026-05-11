#
#  Copyright 2026 The InfiniFlow Authors. All Rights Reserved.
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
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo


CURRENT_TIME_CONTEXT_TAG = "runtime_current_time"
DEFAULT_PROMPT_TIMEZONE = "Asia/Shanghai"


def _runtime_now():
    timezone_name = os.environ.get("RAGFLOW_PROMPT_TIMEZONE", DEFAULT_PROMPT_TIMEZONE).strip() or DEFAULT_PROMPT_TIMEZONE
    try:
        tz = ZoneInfo(timezone_name)
        return datetime.now(tz), timezone_name
    except Exception:
        now = datetime.now().astimezone()
        return now, now.tzname() or "local"


def current_time_context() -> str:
    now, timezone_name = _runtime_now()
    iso_text = now.isoformat(timespec="seconds")
    human_text = now.strftime("%Y-%m-%d %H:%M:%S")
    weekday_text = now.strftime("%A")
    return (
        f"<{CURRENT_TIME_CONTEXT_TAG}>\n"
        f"- Current datetime: {human_text} ({timezone_name}); ISO: {iso_text}.\n"
        f"- Current date: {now.strftime('%Y-%m-%d')} ({weekday_text}).\n"
        "- Treat this runtime value as the authoritative current time for today, yesterday, tomorrow, this week, "
        "this month, deadlines, and other relative-date questions unless the user explicitly provides another date.\n"
        f"</{CURRENT_TIME_CONTEXT_TAG}>"
    )


def append_current_time_context(prompt: str) -> str:
    prompt = prompt or ""
    prompt = re.sub(
        rf"\n*\s*<{CURRENT_TIME_CONTEXT_TAG}>.*?</{CURRENT_TIME_CONTEXT_TAG}>\s*",
        "\n\n",
        prompt,
        flags=re.DOTALL | re.IGNORECASE,
    ).strip()
    if prompt:
        return f"{prompt}\n\n{current_time_context()}"
    return current_time_context()
