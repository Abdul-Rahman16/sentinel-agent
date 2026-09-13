import json

from sqlalchemy.orm import Session

from core.llm import call_llm
from core.logging import log
from domain.agent import check_budget, record_step, request_approval, fail_run, BudgetExceededError
from domain.models import Run
from tools.web_search import web_search
from tools.calculator import calculator

TOOLS = {"web_search": web_search, "calculator": calculator}

PLANNER_SYSTEM = """You are a research planning assistant. Given a question, break it into
2-4 concrete steps using only these tools: web_search (args: query) and calculator (args: expression).
Respond ONLY with a JSON array, no other text. Example:
[{"tool": "web_search", "args": {"query": "..."}}]
If a tool isn't needed, omit it. Keep the plan short and directly useful for answering the question."""

REPORT_SYSTEM = """You are a research assistant writing a final report. Given the original question
and evidence gathered from tool calls, write a clear, well-cited answer. Reference sources by URL where
evidence came from web search. If the evidence is insufficient, say so honestly rather than guessing."""


def make_plan(question: str) -> list[dict]:
    result = call_llm(prompt=f"Question: {question}", system=PLANNER_SYSTEM, max_tokens=512)
    text = result["text"].strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        plan = json.loads(text)
        if not isinstance(plan, list):
            raise ValueError("Plan must be a JSON array")
        return plan
    except (json.JSONDecodeError, ValueError) as e:
        log.warning("plan_parse_failed", error=str(e), raw_text=text)
        return []


def execute_step(db: Session, run: Run, step_spec: dict) -> dict:
    check_budget(db, run)  # hard stop before any tool call — not a suggestion
    tool_name = step_spec.get("tool")
    args = step_spec.get("args", {})
    tool_fn = TOOLS.get(tool_name)

    if tool_fn is None:
        output = {"error": f"Unknown tool: {tool_name}"}
        status = "failed"
    else:
        output = tool_fn(**args)
        status = "failed" if "error" in output else "success"

    record_step(db, run, tool=tool_name or "unknown", input_data=args, output_data=output, tokens_used=0, status=status)
    return output


def synthesize_report(question: str, evidence: list[dict]) -> dict:
    evidence_text = json.dumps(evidence, indent=2)
    return call_llm(
        prompt=f"Original question: {question}\n\nEvidence gathered:\n{evidence_text}\n\nWrite the final report.",
        system=REPORT_SYSTEM,
        max_tokens=1024,
    )


def run_agent(db: Session, run: Run) -> Run:
    """Deliberately NOT a framework-driven agent loop — every step here is explicit
    and auditable, which is the actual point for a governed, bounded-autonomy agent."""
    try:
        plan = make_plan(run.question)
        if not plan:
            return fail_run(db, run, "Could not generate a valid plan for this question.")

        evidence = []
        for step_spec in plan:
            try:
                output = execute_step(db, run, step_spec)
                evidence.append({"tool": step_spec.get("tool"), "output": output})
            except BudgetExceededError:
                break  # stop executing further steps, but still report on what we have

        report_result = synthesize_report(run.question, evidence)
        run.spent_tokens += report_result.get("tokens_used", 0)
        run.final_report = report_result["text"]

        # Any run that produces a report requires human approval before it's
        # considered "published" — this is the actual guardrail, not decoration.
        request_approval(db, run, action_description="Publish final research report")
        db.commit()
        db.refresh(run)
        return run

    except BudgetExceededError:
        return run
    except Exception as e:
        log.error("run_agent_failed", run_id=str(run.id), error=str(e))
        return fail_run(db, run, f"Unexpected error: {e}")