"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth-context";
import type { Connection } from "@/lib/types";
import Button from "@/components/Button";
import Card from "@/components/Card";
import ConfirmButton from "@/components/ConfirmButton";
import ConnectionSubNav from "@/components/ConnectionSubNav";
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
    document.title = "Settings · Watchdog";
  }, []);

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
      <ConnectionSubNav connectionId={connectionId} />

      <h1 className="mb-6 text-2xl font-semibold tracking-[-0.01em] text-ink">Settings</h1>

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
        {error && (
          <p role="alert" className="text-sm text-failing">
            {error}
          </p>
        )}
        {success && (
          <p role="status" className="animate-enter text-sm text-healthy">
            Saved.
          </p>
        )}
        <Button type="submit" disabled={saving} className="self-start">
          {saving ? "Saving..." : "Save changes"}
        </Button>
      </form>

      <Card className="border-failing/40">
        <h2 className="mb-2 text-sm font-medium text-failing">Delete connection</h2>
        <p className="mb-3 text-xs text-muted">
          Permanently removes this connection along with all synced workflows, executions, and alert history.
        </p>
        <ConfirmButton
          onConfirm={handleDelete}
          pending={deleting}
          pendingLabel="Deleting..."
          prompt="Delete this connection and all its history?"
        >
          Delete connection
        </ConfirmButton>
      </Card>
    </div>
  );
}
