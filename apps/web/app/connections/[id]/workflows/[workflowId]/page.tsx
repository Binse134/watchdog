"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import { formatDate } from "@/lib/format";
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
    if (!user) return;
    let ignore = false;
    api
      .get<Workflow>(`/connections/${connectionId}/workflows/${workflowId}`)
      .then((wf) => {
        if (!ignore) setWorkflow(wf);
      })
      .catch((err) => {
        if (!ignore) setError(err instanceof ApiError ? err.message : "Could not load this workflow");
      });
    return () => {
      ignore = true;
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
        className="focus-ring rounded-[4px] text-sm text-muted transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent"
      >
        ← Back to workflows
      </Link>

      {error && <p className="mt-4 text-sm text-failing">{error}</p>}

      {!workflow && !error && <p className="mt-4 text-sm text-muted">Loading…</p>}

      {workflow && (
        <>
          <div className="mt-4 mb-2 flex items-center justify-between gap-4">
            <h1 className="text-2xl font-semibold tracking-[-0.01em] text-ink">{workflow.name}</h1>
            <StatusBadge status={workflow.health_status} />
          </div>

          <p className="mb-6 font-mono text-sm text-muted">
            {workflow.enabled ? "Enabled" : "Disabled"} · last synced {formatDate(workflow.last_synced_at)}
          </p>

          <div className="mb-8 grid grid-cols-2 gap-4 text-sm">
            <Card className="px-4 py-3">
              <p className="text-muted">Last 7 days</p>
              <p className="font-mono text-ink">
                {workflow.run_count_7d} runs, {workflow.error_count_7d} errors
              </p>
            </Card>
            <Card className="px-4 py-3">
              <p className="text-muted">Last 30 days</p>
              <p className="font-mono text-ink">
                {workflow.run_count_30d} runs, {workflow.error_count_30d} errors
              </p>
            </Card>
          </div>

          <Card>
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-medium text-ink">Summary</h2>
              <Button onClick={handleGenerateSummary} disabled={generating} className="px-3 py-1.5 text-xs">
                {generating ? "Generating..." : workflow.summary ? "Regenerate" : "Generate summary"}
              </Button>
            </div>

            {generating && (
              <p className="mb-3 text-xs text-muted">
                This calls a local LLM and can take up to a couple of minutes — feel free to wait.
              </p>
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
        </>
      )}
    </div>
  );
}
