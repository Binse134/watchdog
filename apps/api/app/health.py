from app.models import Workflow
from app.sync import ERROR_STATUSES, WorkflowCounts

HEALTHY = "healthy"
FAILING = "failing"
SILENT = "silent"
UNUSED = "unused"

# Statuses worth emailing the user about - see compute_health_status for what
# each one means. healthy/unused are normal, expected states.
ALERTABLE_STATUSES = {FAILING, SILENT}


def compute_health_status(workflow: Workflow, counts: WorkflowCounts) -> str:
    """Derives a workflow's current health from its sync state and recent
    execution counts. Computed on demand (not stored) so it's always fresh,
    same as the run/error counts it's built from.

    Precedence (first match wins):
    - unused: never executed in the last 30d.
    - silent: ran at some point in the last 30d, but nothing in the last 7 -
      it went quiet despite having a history of running.
    - failing: has run in the last 7d, and the most recent run errored.
    - healthy: has run in the last 7d, and the most recent run succeeded.

    A workflow deleted in n8n is removed from our DB entirely during sync
    (see app/sync.py's _delete_orphaned_workflows) rather than represented
    as a status here.

    A disabled (n8n "inactive") workflow is always unused, regardless of
    its run history - it's not meant to be running, so it's not worth
    alerting on.
    """
    if counts.run_count_30d == 0 or not workflow.enabled:
        return UNUSED
    if counts.run_count_7d == 0:
        return SILENT
    if counts.latest_status in ERROR_STATUSES:
        return FAILING
    return HEALTHY
