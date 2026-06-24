from app.health import FAILING, HEALTHY, ORPHANED, SILENT, UNUSED, compute_health_status
from app.sync import WorkflowCounts


class FakeWorkflow:
    def __init__(self, enabled: bool = True, is_orphaned: bool = False):
        self.enabled = enabled
        self.is_orphaned = is_orphaned


def test_orphaned_wins_over_everything_else():
    workflow = FakeWorkflow(enabled=True, is_orphaned=True)
    counts = WorkflowCounts(run_count_7d=5, run_count_30d=5, latest_status="success")
    assert compute_health_status(workflow, counts) == ORPHANED


def test_disabled_workflow_is_unused_even_with_recent_runs():
    workflow = FakeWorkflow(enabled=False)
    counts = WorkflowCounts(run_count_7d=5, run_count_30d=5, latest_status="success")
    assert compute_health_status(workflow, counts) == UNUSED


def test_enabled_but_never_run_is_unused():
    workflow = FakeWorkflow(enabled=True)
    counts = WorkflowCounts(run_count_30d=0)
    assert compute_health_status(workflow, counts) == UNUSED


def test_ran_in_30d_but_not_7d_is_silent():
    workflow = FakeWorkflow(enabled=True)
    counts = WorkflowCounts(run_count_7d=0, run_count_30d=3, latest_status="success")
    assert compute_health_status(workflow, counts) == SILENT


def test_latest_run_in_7d_is_error_status_means_failing():
    workflow = FakeWorkflow(enabled=True)
    counts = WorkflowCounts(run_count_7d=2, run_count_30d=2, latest_status="error")
    assert compute_health_status(workflow, counts) == FAILING


def test_latest_run_crashed_also_counts_as_failing():
    workflow = FakeWorkflow(enabled=True)
    counts = WorkflowCounts(run_count_7d=1, run_count_30d=1, latest_status="crashed")
    assert compute_health_status(workflow, counts) == FAILING


def test_latest_run_success_in_7d_is_healthy():
    workflow = FakeWorkflow(enabled=True)
    counts = WorkflowCounts(run_count_7d=1, run_count_30d=1, latest_status="success")
    assert compute_health_status(workflow, counts) == HEALTHY
