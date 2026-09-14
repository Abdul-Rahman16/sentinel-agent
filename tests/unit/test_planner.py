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


def test_run_agent_synthesizes_report_successfully():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from core.db import Base
    from domain.agent import create_run
    from domain.planner import run_agent

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    run = create_run(db, question="What is 2+2?", budget_tokens=10000, max_steps=5)

    with patch("domain.planner.make_plan") as mock_plan, \
         patch("domain.planner.execute_step") as mock_exec, \
         patch("domain.planner.synthesize_report") as mock_synth, \
         patch("domain.planner.verify_report") as mock_verify:

        mock_plan.return_value = [{"tool": "calculator", "args": {"expression": "2+2"}}]
        mock_exec.return_value = {"result": 4}
        mock_synth.return_value = {"text": "The result is 4.", "tokens_used": 100}
        mock_verify.return_value = []

        result_run = run_agent(db, run)

        assert result_run.status == "awaiting_approval"
        assert result_run.final_report == "The result is 4."
        assert result_run.spent_tokens == 100

    db.close()
