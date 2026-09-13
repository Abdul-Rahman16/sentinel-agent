import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from domain.models import Run, Step, Approval


class BudgetExceededError(Exception):
    pass


def create_run(db: Session, question: str, budget_tokens: int = 20000, max_steps: int = 10) -> Run:
    run = Run(
        id=uuid.uuid4(),
        question=question,
        status="planning",
        budget_tokens=budget_tokens,
        max_steps=max_steps,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def check_budget(db: Session, run: Run) -> None:
    """Hard stop, not a suggestion. Called before every tool call.
    Persists the budget_exceeded status immediately, not just in memory."""
    if run.spent_tokens >= run.budget_tokens or run.steps_taken >= run.max_steps:
        run.status = "budget_exceeded"
        db.commit()
        raise BudgetExceededError(
            f"Run {run.id} exceeded budget (tokens: {run.spent_tokens}/{run.budget_tokens}, "
            f"steps: {run.steps_taken}/{run.max_steps})"
        )


def record_step(
    db: Session,
    run: Run,
    tool: str,
    input_data: dict,
    output_data: dict | None,
    tokens_used: int,
    status: str = "success",
) -> Step:
    step = Step(
        id=uuid.uuid4(),
        run_id=run.id,
        step_number=run.steps_taken + 1,
        tool=tool,
        input=input_data,
        output=output_data,
        status=status,
        tokens_used=tokens_used,
    )
    db.add(step)

    run.steps_taken += 1
    run.spent_tokens += tokens_used
    run.status = "running"

    db.commit()
    db.refresh(step)
    return step


def request_approval(db: Session, run: Run, action_description: str) -> Approval:
    approval = Approval(
        id=uuid.uuid4(),
        run_id=run.id,
        action_description=action_description,
    )
    db.add(approval)
    run.status = "awaiting_approval"
    db.commit()
    db.refresh(approval)
    return approval


def decide_approval(db: Session, approval: Approval, approved: bool) -> Approval:
    approval.decision = "approved" if approved else "rejected"
    approval.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(approval)
    return approval


def complete_run(db: Session, run: Run, final_report: str) -> Run:
    run.status = "completed"
    run.final_report = final_report
    db.commit()
    db.refresh(run)
    return run


def fail_run(db: Session, run: Run, reason: str) -> Run:
    run.status = "failed"
    run.final_report = reason
    db.commit()
    db.refresh(run)
    return run