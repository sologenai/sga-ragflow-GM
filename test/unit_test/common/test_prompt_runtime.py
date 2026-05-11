import re

from common.prompt_runtime import CURRENT_TIME_CONTEXT_TAG, append_current_time_context


def test_append_current_time_context_adds_runtime_context():
    prompt = append_current_time_context("You are an assistant.")

    assert "You are an assistant." in prompt
    assert f"<{CURRENT_TIME_CONTEXT_TAG}>" in prompt
    assert "Current datetime" in prompt


def test_append_current_time_context_replaces_stale_context():
    old = (
        "Base prompt\n\n"
        f"<{CURRENT_TIME_CONTEXT_TAG}>\n"
        "- Current datetime: 2000-01-01 00:00:00 (Asia/Shanghai).\n"
        f"</{CURRENT_TIME_CONTEXT_TAG}>"
    )

    prompt = append_current_time_context(old)

    assert "Base prompt" in prompt
    assert "2000-01-01" not in prompt
    assert len(re.findall(rf"<{CURRENT_TIME_CONTEXT_TAG}>", prompt)) == 1
