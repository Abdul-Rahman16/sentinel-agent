import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RunSubmitRequest(BaseModel):
    question: str
    budget_tokens: int = 20000
    max_steps: int = 10


class RunResponse(BaseModel):
    id: uuid.UUID
    question: str
    status: str
    spent_tokens: int
    budget_tokens: int
    steps_taken: int
    max_steps: int
    final_report: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class StepResponse(BaseModel):
    id: uuid.UUID
    step_number: int
    tool: str
    input: dict
    output: Optional[dict]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    action_description: str
    decision: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalDecisionRequest(BaseModel):
    approved: bool