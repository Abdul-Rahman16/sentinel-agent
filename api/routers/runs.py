from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select

from core.db import get_db
from core.limiter import limiter
from core.auth import get_current_user_id
from domain.models import Run, Step, Approval
from domain.agent import create_run, decide_approval
from domain.planner import run_agent
from api.schemas import RunSubmitRequest, RunResponse, StepResponse, ApprovalResponse, ApprovalDecisionRequest

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunResponse)
@limiter.limit("10/minute")
def submit_run(
    req: RunSubmitRequest,
    request: Request,
    db: Session = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
):
    run = create_run(db, question=req.question, budget_tokens=req.budget_tokens, max_steps=req.max_steps)
    run.user_id = user_id  # None for anonymous demo runs
    db.commit()
    run = run_agent(db, run)
    return run


@router.get("", response_model=list[RunResponse])
def list_runs(
    db: Session = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
    limit: int = 50,
):
    if user_id is None:
        return []  # anonymous visitors see no history — demo runs aren't listed for anyone
    return db.execute(
        select(Run).where(Run.user_id == user_id).order_by(Run.created_at.desc()).limit(limit)
    ).scalars().all()


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    user_id: str | None = Depends(get_current_user_id),
):
    run = db.execute(select(Run).where(Run.id == run_id)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    # A signed-in user can only fetch their OWN runs by id — anonymous demo
    # runs remain visible by direct id (e.g. right after submitting one).
    if run.user_id is not None and run.user_id != user_id:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status == "failed":
        run.final_report = None
    return run


@router.get("/{run_id}/steps", response_model=list[StepResponse])
def get_run_steps(run_id: str, db: Session = Depends(get_db)):
    return db.execute(select(Step).where(Step.run_id == run_id).order_by(Step.step_number)).scalars().all()


@router.get("/{run_id}/approvals", response_model=list[ApprovalResponse])
def get_run_approvals(run_id: str, db: Session = Depends(get_db)):
    return db.execute(select(Approval).where(Approval.run_id == run_id)).scalars().all()


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalResponse)
def decide_run_approval(approval_id: str, req: ApprovalDecisionRequest, db: Session = Depends(get_db)):
    approval = db.execute(select(Approval).where(Approval.id == approval_id)).scalar_one_or_none()
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    approval = decide_approval(db, approval, req.approved)

    run = db.execute(select(Run).where(Run.id == approval.run_id)).scalar_one_or_none()
    if run:
        run.status = "completed" if req.approved else "failed"
        db.commit()

    return approval