from app.models import Workflow
from app.sync import ERROR_STATUSES, WorkflowCounts

HEALTHY = "healthy"
FAILING = "failing"
SILENT = "silent"
UNUSED = "unused"
ORPHANED = "orphaned"

# Statuses worth emailing the user about - see compute_health_status for what
# each one means. healthy/unused are normal, expected states.
ALERTABLE_STATUSES = {FAILING, SILENT, ORPHANED}


def compute_health_status(workflow: Workflow, counts: WorkflowCounts) -> str:
    """Derives a workflow's current health from its sync state and recent
    execution counts. Computed on demand (not stored) so it's always fresh,
    same as the run/error counts it's built from.

    Precedence (first match wins):
    - orphaned: deleted in n8n but still tracked here.
    - unused: disabled in n8n, or enabled but never executed in the last 30d.
    - silent: ran at some point in the last 30d, but nothing in the last 7 -
      it went quiet despite having a history of running.
    - failing: has run in the last 7d, and the most recent run errored.
    - healthy: has run in the last 7d, and the most recent run succeeded.
    """
    if workflow.is_orphaned:
        return ORPHANED
    if not workflow.enabled or counts.run_count_30d == 0:
        return UNUSED
    if counts.run_count_7d == 0:
        return SILENT
    if counts.latest_status in ERROR_STATUSES:
        return FAILING
    return HEALTHY
