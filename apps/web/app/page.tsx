"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import type { Connection } from "@/lib/types";
import Button from "@/components/Button";
import Card from "@/components/Card";
import Input from "@/components/Input";

/** Calm Default Rule applied to sync status: only a real failure gets a filled pill. */
function SyncStatusBadge({ status }: { status: string }) {
  if (status === "ok") {
    return (
      <span className="inline-flex items-center gap-1.5 font-mono text-xs text-muted">
        <span className="h-1.5 w-1.5 flex-none rounded-full bg-healthy" />
        ok
      </span>
    );
  }
  // text-white, not the system-default #0a0a0a -- see StatusBadge.tsx's comment,
  // same measured contrast failure applies to this twin failing-pill pattern.
  return (
    <span className="inline-flex items-center rounded-full bg-failing px-2.5 py-0.5 font-mono text-xs font-medium tracking-[0.02em] text-white">
      {status}
    </span>
  );
}

export default function DashboardPage() {
  const { user, loading } = useRequireAuth();
  const router = useRouter();

  const [connections, setConnections] = useState<Connection[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    document.title = "Connections · Watchdog";
  }, []);

  useEffect(() => {
    if (!user) return;
    let ignore = false;

    function load() {
      api
        .get<Connection[]>("/connections")
        .then((data) => {
          if (!ignore) setConnections(data);
        })
        .catch((err) => {
          if (!ignore) setListError(err instanceof ApiError ? err.message : "Could not load connections");
        });
    }

    load();
    // Background syncing happens server-side on its own schedule; poll so
    // sync status reflects it without requiring a manual reload.
    const interval = setInterval(load, 15000);
    return () => {
      ignore = true;
      clearInterval(interval);
    };
  }, [user]);

  async function handleConnect(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const connection = await api.post<Connection>("/connections", { n8n_base_url: baseUrl, api_key: apiKey });
      router.push(`/connections/${connection.id}`);
    } catch (err) {
      setFormError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !user) return null;

  return (
    <div className="max-w-2xl mx-auto mt-12 px-4">
      <h1 className="mb-6 text-2xl font-semibold tracking-[-0.01em] text-ink">Your connections</h1>

      {listError && (
        <p role="alert" className="mb-4 text-sm text-failing">
          {listError}
        </p>
      )}

      {!connections && !listError && <p className="mb-4 text-sm text-muted">Loading…</p>}

      {connections && connections.length > 0 && (
        <ul className="mb-8 flex flex-col gap-2">
          {connections.map((c, i) => (
            <li key={c.id} className="animate-enter" style={{ animationDelay: `${Math.min(i, 6) * 30}ms` }}>
              <Link
                href={`/connections/${c.id}`}
                className="focus-ring flex items-start justify-between gap-3 rounded-[10px] border border-hairline bg-panel px-4 py-3 transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:border-accent"
              >
                <span className="min-w-0 break-all font-mono text-sm text-ink">{c.n8n_base_url}</span>
                <span className="mt-0.5 flex-none">
                  <SyncStatusBadge status={c.last_sync_status} />
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}

      {connections && connections.length === 0 && (
        <p className="mb-8 text-sm text-muted">No connections yet — add your n8n instance below to get started.</p>
      )}

      <Card>
        <h2 className="mb-3 text-base font-medium text-ink">Connect an n8n instance</h2>
        <form onSubmit={handleConnect} className="flex flex-col gap-3">
          <label className="text-sm text-muted">
            n8n base URL
            <Input
              type="text"
              required
              placeholder="e.g. http://localhost:5678"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              className="mt-1"
            />
          </label>
          <label className="text-sm text-muted">
            API key
            <Input
              type="password"
              required
              placeholder="From n8n's Settings → API"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="mt-1"
            />
          </label>
          {formError && (
            <p role="alert" className="text-sm text-failing">
              {formError}
            </p>
          )}
          <Button type="submit" disabled={submitting} className="self-start">
            {submitting ? "Connecting..." : "Connect"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
