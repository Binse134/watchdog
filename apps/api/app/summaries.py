import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.llm import generate_text
from app.models import Workflow, WorkflowSummary

# Per-node parameter excerpt cap, to keep the prompt a reasonable size even
# for nodes with large inline code (e.g. Code/Function nodes).
PARAMETER_EXCERPT_CHARS = 300


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def compute_definition_hash(raw_workflow: dict) -> str:
    """Hashes the parts of a workflow that affect its behavior - node names,
    types, and parameters, plus the connection graph. Deliberately excludes
    fields like position/versionId/pinData/meta that change without the
    workflow's actual behavior changing, so e.g. dragging a node around the
    canvas doesn't invalidate the cached summary."""
    nodes = sorted(
        (
            {"name": node["name"], "type": node["type"], "parameters": node.get("parameters", {})}
            for node in raw_workflow.get("nodes", [])
        ),
        key=lambda node: node["name"],
    )
    payload = json.dumps({"nodes": nodes, "connections": raw_workflow.get("connections", {})}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def _format_node(node: dict) -> str:
    node_type = node["type"].removeprefix("n8n-nodes-base.").removeprefix("n8n-nodes-langchain.")
    params_excerpt = json.dumps(node.get("parameters", {}))[:PARAMETER_EXCERPT_CHARS]
    return f"- {node['name']} ({node_type}): {params_excerpt}"


def _format_connections(connections: dict) -> list[str]:
    """n8n's connections dict is {source_name: {output_type: [[{node, type,
    index}, ...], ...]}} - the outer list index is the output branch (e.g.
    an IF node's true/false outputs). Flattened here into "A -> B" lines."""
    lines = []
    for source_name, outputs_by_type in connections.items():
        for branches in outputs_by_type.values():
            for branch_index, branch in enumerate(branches):
                for target in branch:
                    target_name = target.get("node")
                    if len(branches) > 1:
                        lines.append(f"{source_name} -> {target_name} (branch {branch_index})")
                    else:
                        lines.append(f"{source_name} -> {target_name}")
    return lines


def _build_analysis_prompt(raw_workflow: dict) -> str:
    nodes_section = "\n".join(_format_node(node) for node in raw_workflow.get("nodes", []))
    connections_section = "\n".join(_format_connections(raw_workflow.get("connections", {}))) or "(no connections)"

    return (
        "Below is the technical definition of an automation workflow: its "
        "steps, their settings, and the order they run in. Explain step by "
        "step what this workflow accomplishes and why, in as much detail as "
        "needed to be accurate.\n\n"
        f"Workflow name: {raw_workflow.get('name')}\n\n"
        f"Steps:\n{nodes_section}\n\n"
        f"Step order (execution flow):\n{connections_section}\n"
    )


def _build_condense_prompt(analysis: str) -> str:
    return (
        "Condense the following technical workflow analysis into 2 to 4 "
        "plain English sentences for a non-technical reader. Write flowing "
        "prose only - absolutely no markdown, no headers, no bullet "
        "points, no tables, no numbered lists. Do not mention technical "
        "terms, node names, or step names - describe what happens in "
        "everyday language instead. Output ONLY the final sentences, "
        "nothing else - no preamble.\n\n"
        f"{analysis}"
    )


def generate_workflow_summary(
    db: Session, workflow: Workflow, raw_workflow: dict, force: bool = False
) -> WorkflowSummary:
    """Returns a cached summary if the workflow's definition hasn't changed
    since it was generated; otherwise (or if force=True) calls the LLM for a
    fresh one and persists it. Raises LlmError on generation failure - the
    caller decides how to surface that (this is a synchronous, user-
    triggered action, not a background job, so silently swallowing the
    error like app/email.py does would hide a real failure from the user).

    Two LLM calls, not one: asking directly for a short plain-English
    summary from the raw node/connection list reliably got ignored in
    testing (gemma4:e4b wrote multi-section technical reports regardless of
    formatting instructions; qwen3:14b rendered an ASCII node-graph tree).
    Both models stay on-task when asked to produce a thorough analysis
    first, then separately condense *that text* into plain sentences - so
    that's the only thing this calls the LLM for in two steps."""
    definition_hash = compute_definition_hash(raw_workflow)
    existing = db.query(WorkflowSummary).filter(WorkflowSummary.workflow_id == workflow.id).first()

    if existing and existing.definition_hash == definition_hash and not force:
        return existing

    analysis = generate_text(_build_analysis_prompt(raw_workflow))
    summary_text = generate_text(_build_condense_prompt(analysis))

    is_new = existing is None
    if is_new:
        existing = WorkflowSummary(workflow_id=workflow.id)
        db.add(existing)

    existing.definition_hash = definition_hash
    existing.summary = summary_text
    existing.generated_at = now_utc()

    try:
        db.commit()
    except IntegrityError:
        # A concurrent request for the same workflow (e.g. a double-click)
        # won the insert race while this one was waiting on the LLM calls -
        # fall back to updating the row it just created instead of 500ing.
        db.rollback()
        if not is_new:
            raise
        existing = db.query(WorkflowSummary).filter(WorkflowSummary.workflow_id == workflow.id).one()
        existing.definition_hash = definition_hash
        existing.summary = summary_text
        existing.generated_at = now_utc()
        db.commit()

    db.refresh(existing)
    return existing
