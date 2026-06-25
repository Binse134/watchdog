"use client";

import { Suspense, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import Button from "@/components/Button";
import Input from "@/components/Input";

function ResetPasswordForm() {
  const token = useSearchParams().get("token");
  const router = useRouter();

  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: newPassword });
      router.push("/login");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <p role="alert" className="text-sm text-failing">
        This reset link is missing its token. Request a new one from{" "}
        <Link href="/forgot-password" className="focus-ring rounded-[2px] text-accent hover:underline">
          here
        </Link>
        .
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3">
      <label className="text-sm text-muted">
        New password
        <Input
          type="password"
          required
          minLength={8}
          autoComplete="new-password"
          placeholder="Min 8 characters"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="mt-1"
        />
      </label>
      {error && (
        <p role="alert" className="text-sm text-failing">
          {error}
        </p>
      )}
      <Button type="submit" disabled={submitting}>
        {submitting ? "Saving..." : "Set new password"}
      </Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  useEffect(() => {
    document.title = "Set new password · Watchdog";
  }, []);

  return (
    <div className="animate-enter max-w-sm mx-auto mt-16 px-4">
      <h1 className="mb-6 text-2xl font-semibold tracking-[-0.01em] text-ink">Set a new password</h1>
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
