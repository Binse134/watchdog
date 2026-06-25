"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import { formatDate, pluralize } from "@/lib/format";
import type { Workflow, WorkflowSummary } from "@/lib/types";
import Button from "@/components/Button";
import Card from "@/components/Card";
import StatusBadge from "@/components/StatusBadge";

export default function WorkflowDetailPage() {
  const { user, loading } = useRequireAuth();
  const params = useParams<{ id: string; workflowId: string }>();
  const { id: connectionId, workflowId } = params;

  const [workflow, setWorkflow] = useState<Workflow | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    if (workflow?.name) {
      document.title = `${workflow.name} · Watchdog`;
    }
  }, [workflow?.name]);

  useEffect(() => {
    if (!user) return;
    let ignore = false;

    function load() {
      api
        .get<Workflow>(`/connections/${connectionId}/workflows/${workflowId}`)
        .then((wf) => {
          if (!ignore) setWorkflow(wf);
        })
        .catch((err) => {
          if (!ignore) setError(err instanceof ApiError ? err.message : "Could not load this workflow");
        });
    }

    load();
    // Background syncing happens server-side on its own schedule; poll so
    // this view reflects it without requiring a manual reload.
    const interval = setInterval(load, 15000);
    return () => {
      ignore = true;
      clearInterval(interval);
    };
  }, [user, connectionId, workflowId]);

  async function handleGenerateSummary() {
    setGenerating(true);
    setError(null);
    try {
      const force = Boolean(workflow?.summary);
      const result = await api.post<WorkflowSummary>(
        `/connections/${connectionId}/workflows/${workflowId}/summary?force=${force}`,
      );
      setWorkflow((prev) => (prev ? { ...prev, summary: result.summary, summary_generated_at: result.generated_at } : prev));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not generate a summary");
    } finally {
      setGenerating(false);
    }
  }

  if (loading || !user) return null;

  return (
    <div className="max-w-2xl mx-auto mt-12 px-4">
      <Link
        href={`/connections/${connectionId}`}
        className="focus-ring inline-block rounded-[4px] py-1.5 text-sm text-muted transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent pointer-coarse:py-3"
      >
        ← Back to workflows
      </Link>

      {error && (
        <p role="alert" className="mt-4 text-sm text-failing">
          {error}
        </p>
      )}

      {!workflow && !error && <p className="mt-4 text-sm text-muted">Loading…</p>}

      {workflow && (
        <div className="animate-enter">
          <div className="mt-4 mb-2 flex items-start justify-between gap-4">
            <h1 className="min-w-0 text-2xl font-semibold tracking-[-0.01em] text-ink">{workflow.name}</h1>
            <span className="mt-1 flex-none">
              <StatusBadge status={workflow.health_status} />
            </span>
          </div>

          <p className="mb-6 font-mono text-sm text-muted">
            {workflow.enabled ? "Enabled" : "Disabled"} · last synced {formatDate(workflow.last_synced_at)}
          </p>

          <div className="mb-8 grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
            <Card className="px-4 py-3">
              <p className="text-muted">Last 7 days</p>
              <p className="font-mono text-ink">
                {pluralize(workflow.run_count_7d, "run")}, {pluralize(workflow.error_count_7d, "error")}
              </p>
            </Card>
            <Card className="px-4 py-3">
              <p className="text-muted">Last 30 days</p>
              <p className="font-mono text-ink">
                {pluralize(workflow.run_count_30d, "run")}, {pluralize(workflow.error_count_30d, "error")}
              </p>
            </Card>
          </div>

          <Card>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-medium text-ink">Summary</h2>
              <Button
                onClick={handleGenerateSummary}
                disabled={generating}
                className="px-3 py-1.5 text-xs pointer-coarse:min-h-11 pointer-coarse:px-4"
              >
                {generating ? "Generating..." : workflow.summary ? "Regenerate" : "Generate summary"}
              </Button>
            </div>

            {generating && (
              <div aria-live="polite" className="mb-3">
                <div className="mb-2 h-1 overflow-hidden rounded-full bg-panel-raised">
                  <div className="animate-indeterminate h-full w-1/3 rounded-full bg-accent" />
                </div>
                <p className="text-xs text-muted">
                  This calls a local LLM and can take up to a couple of minutes — feel free to wait.
                </p>
              </div>
            )}

            {workflow.summary ? (
              <>
                <p className="text-sm text-ink">{workflow.summary}</p>
                <p className="mt-2 font-mono text-xs text-muted">Generated {formatDate(workflow.summary_generated_at)}</p>
              </>
            ) : (
              <p className="text-sm text-muted italic">No summary generated yet.</p>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
