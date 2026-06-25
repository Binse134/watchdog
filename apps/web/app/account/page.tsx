"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth, useRequireAuth } from "@/lib/auth-context";
import Button from "@/components/Button";
import Card from "@/components/Card";
import ConfirmButton from "@/components/ConfirmButton";
import Input from "@/components/Input";

export default function AccountPage() {
  const { user, loading } = useRequireAuth();
  const { refresh } = useAuth();
  const router = useRouter();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Account · Watchdog";
  }, []);

  async function handleChangePassword(e: FormEvent) {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(false);
    setSaving(true);
    try {
      await api.patch("/auth/me/password", { current_password: currentPassword, new_password: newPassword });
      setCurrentPassword("");
      setNewPassword("");
      setPasswordSuccess(true);
    } catch (err) {
      setPasswordError(err instanceof ApiError ? err.message : "Could not change password");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.delete("/auth/me");
      await refresh();
      router.push("/login");
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : "Could not delete account");
      setDeleting(false);
    }
  }

  if (loading || !user) return null;

  return (
    <div className="max-w-sm mx-auto mt-12 px-4">
      <h1 className="mb-1 text-2xl font-semibold tracking-[-0.01em] text-ink">Account</h1>
      <p className="mb-6 font-mono text-xs text-muted">{user.email}</p>

      <form onSubmit={handleChangePassword} className="mb-10 flex flex-col gap-3">
        <h2 className="text-sm font-medium text-ink">Change password</h2>
        <label className="text-sm text-muted">
          Current password
          <Input
            type="password"
            required
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            className="mt-1"
          />
        </label>
        <label className="text-sm text-muted">
          New password
          <Input
            type="password"
            required
            minLength={8}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="mt-1"
          />
        </label>
        {passwordError && (
          <p role="alert" className="text-sm text-failing">
            {passwordError}
          </p>
        )}
        {passwordSuccess && (
          <p role="status" className="animate-enter text-sm text-healthy">
            Password updated.
          </p>
        )}
        <Button type="submit" disabled={saving} className="self-start">
          {saving ? "Saving..." : "Update password"}
        </Button>
      </form>

      <Card className="border-failing/40">
        <h2 className="mb-2 text-sm font-medium text-failing">Delete account</h2>
        <p className="mb-3 text-xs text-muted">
          Permanently removes your account along with every connection, workflow, execution, and alert tied to it.
        </p>
        {deleteError && (
          <p role="alert" className="mb-3 text-sm text-failing">
            {deleteError}
          </p>
        )}
        <ConfirmButton
          onConfirm={handleDelete}
          pending={deleting}
          pendingLabel="Deleting..."
          prompt="Delete your account permanently?"
        >
          Delete account
        </ConfirmButton>
      </Card>
    </div>
  );
}
