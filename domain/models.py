import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from core.db import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(String, nullable=False)
    status = Column(String, nullable=False, default="planning")
    # planning, running, awaiting_approval, completed, failed, budget_exceeded
    budget_tokens = Column(Integer, nullable=False, default=20000)
    spent_tokens = Column(Integer, nullable=False, default=0)
    max_steps = Column(Integer, nullable=False, default=10)
    steps_taken = Column(Integer, nullable=False, default=0)
    final_report = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_runs_status", "status"),
    )


class Step(Base):
    __tablename__ = "steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    step_number = Column(Integer, nullable=False)
    tool = Column(String, nullable=False)  # e.g. "web_search", "calculator", "planner"
    input = Column(JSON, nullable=False, default=dict)
    output = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default="pending")  # pending, success, failed
    tokens_used = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_steps_run_id", "run_id"),
    )


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    action_description = Column(String, nullable=False)
    decision = Column(String, nullable=True)  # null = pending, "approved", "rejected"
    decided_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)