"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import Button from "@/components/Button";
import Input from "@/components/Input";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    document.title = "Reset password · Watchdog";
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSubmitted(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="animate-enter max-w-sm mx-auto mt-16 px-4">
      <h1 className="mb-6 text-2xl font-semibold tracking-[-0.01em] text-ink">Reset your password</h1>
      {submitted ? (
        <p role="status" className="animate-enter text-sm text-muted">
          If that email has an account, a reset link has been sent. Check your inbox.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="text-sm text-muted">
            Email
            <Input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1"
            />
          </label>
          {error && (
            <p role="alert" className="text-sm text-failing">
              {error}
            </p>
          )}
          <Button type="submit" disabled={submitting}>
            {submitting ? "Sending..." : "Send reset link"}
          </Button>
        </form>
      )}
      <p className="mt-4 text-sm text-muted">
        <Link href="/login" className="focus-ring rounded-[2px] text-accent hover:underline">
          Back to log in
        </Link>
      </p>
    </div>
  );
}
