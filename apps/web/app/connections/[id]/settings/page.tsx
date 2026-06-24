"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import type { Connection } from "@/lib/types";
import Button from "@/components/Button";
import Card from "@/components/Card";
import Input from "@/components/Input";

export default function ConnectionSettingsPage() {
  const { user, loading } = useRequireAuth();
  const params = useParams<{ id: string }>();
  const connectionId = params.id;
  const router = useRouter();

  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!user) return;
    let ignore = false;
    api
      .get<Connection>(`/connections/${connectionId}`)
      .then((c) => {
        if (!ignore) setBaseUrl(c.n8n_base_url);
      })
      .catch((err) => {
        if (!ignore) setError(err instanceof ApiError ? err.message : "Could not load this connection");
      });
    return () => {
      ignore = true;
    };
  }, [user, connectionId]);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);
    setSaving(true);
    try {
      const body: { n8n_base_url: string; api_key?: string } = { n8n_base_url: baseUrl };
      if (apiKey) body.api_key = apiKey;
      await api.patch<Connection>(`/connections/${connectionId}`, body);
      setApiKey("");
      setSuccess(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save changes");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm("Delete this connection? This removes all of its synced workflows, executions, and alert history.")) {
      return;
    }
    setDeleting(true);
    try {
      await api.delete(`/connections/${connectionId}`);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not delete this connection");
      setDeleting(false);
    }
  }

  if (loading || !user) return null;

  return (
    <div className="max-w-sm mx-auto mt-12 px-4">
      <Link
        href={`/connections/${connectionId}`}
        className="focus-ring rounded-[4px] text-sm text-muted transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent"
      >
        ← Back to workflows
      </Link>

      <h1 className="mt-4 mb-6 text-2xl font-semibold tracking-[-0.01em] text-ink">Settings</h1>

      <form onSubmit={handleSave} className="mb-10 flex flex-col gap-3">
        <label className="text-sm text-muted">
          n8n base URL
          <Input
            type="text"
            required
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            className="mt-1"
          />
        </label>
        <label className="text-sm text-muted">
          API key
          <Input
            type="password"
            placeholder="Leave blank to keep the current key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="mt-1"
          />
        </label>
        {error && <p className="text-sm text-failing">{error}</p>}
        {success && <p className="text-sm text-healthy">Saved.</p>}
        <Button type="submit" disabled={saving} className="self-start">
          {saving ? "Saving..." : "Save changes"}
        </Button>
      </form>

      <Card className="border-failing/40">
        <h2 className="mb-2 text-sm font-medium text-failing">Delete connection</h2>
        <p className="mb-3 text-xs text-muted">
          Permanently removes this connection along with all synced workflows, executions, and alert history.
        </p>
        <Button variant="danger" onClick={handleDelete} disabled={deleting}>
          {deleting ? "Deleting..." : "Delete connection"}
        </Button>
      </Card>
    </div>
  );
}
