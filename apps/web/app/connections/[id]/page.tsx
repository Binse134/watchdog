"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import { formatDate, pluralize } from "@/lib/format";
import type { Connection, Workflow } from "@/lib/types";
import Button from "@/components/Button";
import ConnectionSubNav from "@/components/ConnectionSubNav";
import StatusBadge from "@/components/StatusBadge";

async function fetchConnectionAndWorkflows(connectionId: string) {
  const [connection, workflows] = await Promise.all([
    api.get<Connection>(`/connections/${connectionId}`),
    api.get<Workflow[]>(`/connections/${connectionId}/workflows`),
  ]);
  return { connection, workflows };
}

export default function ConnectionPage() {
  const { user, loading } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const connectionId = params.id;

  const [connection, setConnection] = useState<Connection | null>(null);
  const [workflows, setWorkflows] = useState<Workflow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    if (connection?.n8n_base_url) {
      document.title = `${connection.n8n_base_url} · Watchdog`;
    }
  }, [connection?.n8n_base_url]);

  useEffect(() => {
    if (!user) return;
    let ignore = false;

    function load() {
      fetchConnectionAndWorkflows(connectionId)
        .then(({ connection, workflows }) => {
          if (ignore) return;
          setConnection(connection);
          setWorkflows(workflows);
        })
        .catch((err) => {
          if (ignore) return;
          setError(err instanceof ApiError ? err.message : "Could not load this connection");
        });
    }

    load();
    // Background syncing happens server-side on its own schedule; poll so
    // this view reflects it without requiring a manual reload or "Sync now".
    const interval = setInterval(load, 15000);
    return () => {
      ignore = true;
      clearInterval(interval);
    };
  }, [user, connectionId]);

  async function handleSync() {
    setSyncing(true);
    setError(null);
    try {
      await api.post(`/connections/${connectionId}/sync`);
      const { connection, workflows } = await fetchConnectionAndWorkflows(connectionId);
      setConnection(connection);
      setWorkflows(workflows);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  }

  if (loading || !user) return null;

  return (
    <div className="max-w-4xl mx-auto mt-12 px-4">
      <ConnectionSubNav connectionId={connectionId} />

      <h1 className="mb-2 break-all font-mono text-2xl font-semibold tracking-[-0.01em] text-ink">
        {connection?.n8n_base_url ?? "Connection"}
      </h1>

      {connection && (
        <p aria-live="polite" className="mb-6 font-mono text-sm text-muted">
          Last sync: {connection.last_sync_status}
          {connection.last_sync_error ? ` — ${connection.last_sync_error}` : ""} ({formatDate(connection.last_sync_at)})
        </p>
      )}

      <Button onClick={handleSync} disabled={syncing} className="mb-6">
        {syncing ? "Syncing..." : "Sync now"}
      </Button>

      {error && (
        <p role="alert" className="mb-4 text-sm text-failing">
          {error}
        </p>
      )}

      {!workflows && !error && <p className="text-sm text-muted">Loading…</p>}

      {workflows && workflows.length === 0 && (
        <p className="text-sm text-muted">No workflows synced yet — click &quot;Sync now&quot; to fetch them from n8n.</p>
      )}

      {workflows && workflows.length > 0 && (
        <div className="flex flex-col gap-2">
          {workflows.map((wf, i) => (
            <Link
              key={wf.id}
              href={`/connections/${connectionId}/workflows/${wf.id}`}
              className="animate-enter focus-ring flex flex-col gap-2 rounded-[10px] border border-hairline bg-panel px-4 py-3 transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:border-accent"
              style={{ animationDelay: `${Math.min(i, 8) * 25}ms` }}
            >
              <div className="flex items-start justify-between gap-3">
                <span className="min-w-0 text-[15px] font-medium text-ink">
                  {wf.name}
                  {!wf.enabled && <span className="font-normal text-muted"> (disabled)</span>}
                </span>
                <span className="mt-0.5 flex-none">
                  <StatusBadge status={wf.health_status} />
                </span>
              </div>
              <div className="font-mono text-xs text-muted">
                <span className="text-ink/70">7d</span> {pluralize(wf.run_count_7d, "run")}, {pluralize(wf.error_count_7d, "error")}
                <span className="mx-2 text-hairline">·</span>
                <span className="text-ink/70">30d</span> {pluralize(wf.run_count_30d, "run")}, {pluralize(wf.error_count_30d, "error")}
              </div>
              <p className="line-clamp-2 text-sm text-muted italic">{wf.summary ?? "No summary generated yet."}</p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
