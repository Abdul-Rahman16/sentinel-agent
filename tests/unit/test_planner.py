from unittest.mock import patch

from domain.planner import make_plan


def test_make_plan_parses_valid_json_array():
    with patch("domain.planner.call_llm") as mock_llm:
        mock_llm.return_value = {"text": '[{"tool": "web_search", "args": {"query": "test"}}]', "tokens_used": 50}
        plan = make_plan("some question")
    assert plan == [{"tool": "web_search", "args": {"query": "test"}}]


def test_make_plan_strips_markdown_code_fences():
    with patch("domain.planner.call_llm") as mock_llm:
        mock_llm.return_value = {"text": '```json\n[{"tool": "calculator", "args": {"expression": "1+1"}}]\n```', "tokens_used": 50}
        plan = make_plan("some question")
    assert plan == [{"tool": "calculator", "args": {"expression": "1+1"}}]


def test_make_plan_returns_empty_list_on_invalid_json():
    with patch("domain.planner.call_llm") as mock_llm:
        mock_llm.return_value = {"text": "not valid json at all", "tokens_used": 50}
        plan = make_plan("some question")
    assert plan == []


def test_make_plan_returns_empty_list_when_not_a_list():
    with patch("domain.planner.call_llm") as mock_llm:
        mock_llm.return_value = {"text": '{"tool": "web_search"}', "tokens_used": 50}
        plan = make_plan("some question")
    assert plan == []