from app.summaries import compute_definition_hash, generate_workflow_summary

RAW_WORKFLOW = {
    "name": "Onboarding",
    "nodes": [
        {"name": "Webhook", "type": "n8n-nodes-base.webhook", "parameters": {"path": "abc"}, "position": [0, 0]},
        {"name": "Send Email", "type": "n8n-nodes-base.emailSend", "parameters": {"to": "a@b.com"}, "position": [100, 0]},
    ],
    "connections": {"Webhook": {"main": [[{"node": "Send Email", "type": "main", "index": 0}]]}},
}


def test_hash_is_stable_for_identical_definition():
    assert compute_definition_hash(RAW_WORKFLOW) == compute_definition_hash(RAW_WORKFLOW)


def test_hash_ignores_node_order():
    reordered = {**RAW_WORKFLOW, "nodes": list(reversed(RAW_WORKFLOW["nodes"]))}
    assert compute_definition_hash(RAW_WORKFLOW) == compute_definition_hash(reordered)


def test_hash_ignores_position_changes():
    moved = {
        **RAW_WORKFLOW,
        "nodes": [{**n, "position": [999, 999]} for n in RAW_WORKFLOW["nodes"]],
    }
    assert compute_definition_hash(RAW_WORKFLOW) == compute_definition_hash(moved)


def test_hash_changes_when_a_parameter_changes():
    changed = {
        **RAW_WORKFLOW,
        "nodes": [
            {**n, "parameters": {**n["parameters"], "to": "different@b.com"}}
            if n["name"] == "Send Email"
            else n
            for n in RAW_WORKFLOW["nodes"]
        ],
    }
    assert compute_definition_hash(RAW_WORKFLOW) != compute_definition_hash(changed)


def test_hash_changes_when_connections_change():
    changed = {**RAW_WORKFLOW, "connections": {}}
    assert compute_definition_hash(RAW_WORKFLOW) != compute_definition_hash(changed)


def test_generate_workflow_summary_calls_llm_twice_and_caches(db, make_user, make_connection, make_workflow, monkeypatch):
    calls = []

    def fake_generate_text(prompt):
        calls.append(prompt)
        return "analysis text" if len(calls) == 1 else "plain summary"

    monkeypatch.setattr("app.summaries.generate_text", fake_generate_text)

    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    result = generate_workflow_summary(db, workflow, RAW_WORKFLOW)

    assert len(calls) == 2
    assert result.summary == "plain summary"
    assert result.definition_hash == compute_definition_hash(RAW_WORKFLOW)


def test_generate_workflow_summary_skips_llm_when_definition_unchanged(
    db, make_user, make_connection, make_workflow, monkeypatch
):
    calls = []
    monkeypatch.setattr("app.summaries.generate_text", lambda prompt: calls.append(prompt) or "text")

    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    generate_workflow_summary(db, workflow, RAW_WORKFLOW)
    assert len(calls) == 2

    generate_workflow_summary(db, workflow, RAW_WORKFLOW)
    assert len(calls) == 2  # no new LLM calls - cache hit


def test_generate_workflow_summary_force_regenerates_even_if_unchanged(
    db, make_user, make_connection, make_workflow, monkeypatch
):
    calls = []
    monkeypatch.setattr("app.summaries.generate_text", lambda prompt: calls.append(prompt) or "text")

    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    generate_workflow_summary(db, workflow, RAW_WORKFLOW)
    assert len(calls) == 2

    generate_workflow_summary(db, workflow, RAW_WORKFLOW, force=True)
    assert len(calls) == 4


def test_generate_workflow_summary_regenerates_when_definition_changes(
    db, make_user, make_connection, make_workflow, monkeypatch
):
    calls = []
    monkeypatch.setattr("app.summaries.generate_text", lambda prompt: calls.append(prompt) or "text")

    user = make_user()
    connection = make_connection(user)
    workflow = make_workflow(connection)

    generate_workflow_summary(db, workflow, RAW_WORKFLOW)
    changed = {**RAW_WORKFLOW, "connections": {}}
    generate_workflow_summary(db, workflow, changed)

    assert len(calls) == 4

    from app.models import WorkflowSummary

    rows = db.query(WorkflowSummary).filter(WorkflowSummary.workflow_id == workflow.id).all()
    assert len(rows) == 1  # upserted in place, no history row
