import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.db import Base
from domain.agent import (
    create_run, check_budget, record_step, request_approval,
    decide_approval, complete_run, fail_run, BudgetExceededError,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_create_run_starts_in_planning_status(db_session):
    run = create_run(db_session, question="test question")
    assert run.status == "planning"
    assert run.spent_tokens == 0
    assert run.steps_taken == 0


def test_check_budget_passes_when_under_limits(db_session):
    run = create_run(db_session, question="test", budget_tokens=1000, max_steps=5)
    check_budget(db_session, run)  # should not raise


def test_check_budget_raises_and_persists_status_when_tokens_exceeded(db_session):
    run = create_run(db_session, question="test", budget_tokens=100, max_steps=5)
    run.spent_tokens = 150
    with pytest.raises(BudgetExceededError):
        check_budget(db_session, run)
    assert run.status == "budget_exceeded"


def test_check_budget_raises_when_max_steps_exceeded(db_session):
    run = create_run(db_session, question="test", budget_tokens=10000, max_steps=2)
    run.steps_taken = 2
    with pytest.raises(BudgetExceededError):
        check_budget(db_session, run)
    assert run.status == "budget_exceeded"


def test_record_step_increments_counters(db_session):
    run = create_run(db_session, question="test")
    step = record_step(db_session, run, tool="web_search", input_data={"query": "x"}, output_data={"results": []}, tokens_used=100)
    assert step.step_number == 1
    assert run.steps_taken == 1
    assert run.spent_tokens == 100
    assert run.status == "running"


def test_request_approval_sets_awaiting_status(db_session):
    run = create_run(db_session, question="test")
    approval = request_approval(db_session, run, action_description="Publish report")
    assert run.status == "awaiting_approval"
    assert approval.decision is None


def test_decide_approval_approved(db_session):
    run = create_run(db_session, question="test")
    approval = request_approval(db_session, run, action_description="Publish report")
    decided = decide_approval(db_session, approval, approved=True)
    assert decided.decision == "approved"
    assert decided.decided_at is not None


def test_decide_approval_rejected(db_session):
    run = create_run(db_session, question="test")
    approval = request_approval(db_session, run, action_description="Publish report")
    decided = decide_approval(db_session, approval, approved=False)
    assert decided.decision == "rejected"


def test_complete_run_sets_status_and_report(db_session):
    run = create_run(db_session, question="test")
    completed = complete_run(db_session, run, final_report="the answer")
    assert completed.status == "completed"
    assert completed.final_report == "the answer"


def test_fail_run_sets_status_and_reason(db_session):
    run = create_run(db_session, question="test")
    failed = fail_run(db_session, run, reason="something broke")
    assert failed.status == "failed"
    assert failed.final_report == "something broke"