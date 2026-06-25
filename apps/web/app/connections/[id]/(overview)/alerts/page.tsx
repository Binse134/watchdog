"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import { formatDate } from "@/lib/format";
import type { Alert } from "@/lib/types";
import Button from "@/components/Button";
import StatusBadge from "@/components/StatusBadge";

type Filter = "all" | "open" | "resolved";

export default function AlertsPage() {
  const { user, loading } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const connectionId = params.id;

  const [filter, setFilter] = useState<Filter>("all");
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Alerts · Watchdog";
  }, []);

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

  async function handleResolve(alertId: string) {
    setResolvingId(alertId);
    setError(null);
    try {
      const resolved = await api.post<Alert>(`/connections/${connectionId}/alerts/${alertId}/resolve`);
      setAlerts((prev) => {
        if (!prev) return prev;
        // "open" filter excludes it now that it's resolved; the others just
        // reflect its updated resolved_at in place.
        if (filter === "open") return prev.filter((a) => a.id !== alertId);
        return prev.map((a) => (a.id === alertId ? resolved : a));
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not resolve this alert");
    } finally {
      setResolvingId(null);
    }
  }

  if (loading || !user) return null;

  return (
    <>
      <h1 className="mb-4 text-2xl font-semibold tracking-[-0.01em] text-ink">Alerts</h1>

      <div className="mb-6 inline-flex gap-1 rounded-[6px] border border-hairline bg-panel p-1 text-sm">
        {(["all", "open", "resolved"] as Filter[]).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`focus-ring cursor-pointer rounded-[4px] px-3 py-1.5 font-mono text-xs transition-[background-color,color,transform] duration-150 [transition-timing-function:var(--ease-out-expo)] active:scale-[0.95] pointer-coarse:min-h-11 pointer-coarse:px-4 ${
              filter === f ? "bg-primary text-[#0a0a0a]" : "text-muted hover:text-ink"
            }`}
          >
            {f === "all" ? "All" : f === "open" ? "Open" : "Resolved"}
          </button>
        ))}
      </div>

      {error && (
        <p role="alert" className="mb-4 text-sm text-failing">
          {error}
        </p>
      )}

      {!alerts && !error && <p className="text-sm text-muted">Loading…</p>}

      {alerts && alerts.length === 0 && <p className="text-sm text-muted">No alerts here.</p>}

      {alerts && alerts.length > 0 && (
        <div className="flex flex-col gap-2">
          {alerts.map((alert, i) => (
            <div
              key={alert.id}
              className="animate-enter rounded-[10px] border border-hairline bg-panel px-4 py-3"
              style={{ animationDelay: `${Math.min(i, 8) * 25}ms` }}
            >
              <div className="mb-1 flex items-start justify-between gap-4">
                <Link
                  href={`/connections/${connectionId}/workflows/${alert.workflow_id}`}
                  className="focus-ring min-w-0 rounded-[4px] text-sm font-medium text-ink hover:underline"
                >
                  {alert.workflow_name}
                </Link>
                <span className="flex-none">
                  <StatusBadge status={alert.alert_type} />
                </span>
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
              {!alert.resolved_at && (
                <Button
                  variant="ghost"
                  onClick={() => handleResolve(alert.id)}
                  disabled={resolvingId === alert.id}
                  className="mt-3 px-3 py-1.5 text-xs"
                >
                  {resolvingId === alert.id ? "Resolving..." : "Resolve"}
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
