"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import { formatDate } from "@/lib/format";
import type { Alert } from "@/lib/types";
import StatusBadge from "@/components/StatusBadge";

type Filter = "all" | "open" | "resolved";

export default function AlertsPage() {
  const { user, loading } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const connectionId = params.id;

  const [filter, setFilter] = useState<Filter>("all");
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    let ignore = false;
    const query = filter === "all" ? "" : `?resolved=${filter === "resolved"}`;
    api
      .get<Alert[]>(`/connections/${connectionId}/alerts${query}`)
      .then((data) => {
        if (!ignore) setAlerts(data);
      })
      .catch((err) => {
        if (!ignore) setError(err instanceof ApiError ? err.message : "Could not load alerts");
      });
    return () => {
      ignore = true;
    };
  }, [user, connectionId, filter]);

  if (loading || !user) return null;

  return (
    <div className="max-w-3xl mx-auto mt-12 px-4">
      <Link
        href={`/connections/${connectionId}`}
        className="focus-ring rounded-[4px] text-sm text-muted transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent"
      >
        ← Back to workflows
      </Link>

      <h1 className="mt-4 mb-4 text-2xl font-semibold tracking-[-0.01em] text-ink">Alerts</h1>

      <div className="mb-6 inline-flex gap-1 rounded-[6px] border border-hairline bg-panel p-1 text-sm">
        {(["all", "open", "resolved"] as Filter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`focus-ring cursor-pointer rounded-[4px] px-3 py-1.5 font-mono text-xs transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] ${
              filter === f ? "bg-primary text-[#0a0a0a]" : "text-muted hover:text-ink"
            }`}
          >
            {f === "all" ? "All" : f === "open" ? "Open" : "Resolved"}
          </button>
        ))}
      </div>

      {error && <p className="mb-4 text-sm text-failing">{error}</p>}

      {!alerts && !error && <p className="text-sm text-muted">Loading…</p>}

      {alerts && alerts.length === 0 && <p className="text-sm text-muted">No alerts here.</p>}

      {alerts && alerts.length > 0 && (
        <div className="flex flex-col gap-2">
          {alerts.map((alert) => (
            <div key={alert.id} className="rounded-[10px] border border-hairline bg-panel px-4 py-3">
              <div className="mb-1 flex items-center justify-between gap-4">
                <Link
                  href={`/connections/${connectionId}/workflows/${alert.workflow_id}`}
                  className="focus-ring rounded-[4px] text-sm font-medium text-ink hover:underline"
                >
                  {alert.workflow_name}
                </Link>
                <StatusBadge status={alert.alert_type} />
              </div>
              <p className="font-mono text-xs text-muted">
                Triggered {formatDate(alert.triggered_at)} ·{" "}
                {alert.resolved_at ? `Resolved ${formatDate(alert.resolved_at)}` : "Still open"}
              </p>
              <p className="mt-1 font-mono text-xs text-muted">
                {alert.email_sent_at
                  ? `Email sent ${formatDate(alert.email_sent_at)}`
                  : alert.email_error
                    ? `Email not sent: ${alert.email_error}`
                    : "Email pending"}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
