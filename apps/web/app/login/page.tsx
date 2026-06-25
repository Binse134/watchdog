"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { User } from "@/lib/types";
import Button from "@/components/Button";
import Input from "@/components/Input";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { refresh } = useAuth();
  const router = useRouter();

  useEffect(() => {
    document.title = "Log in · Watchdog";
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.post<User>("/auth/login", { email, password });
      await refresh();
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="animate-enter max-w-sm mx-auto mt-16 px-4">
      <h1 className="mb-1 text-2xl font-semibold tracking-[-0.01em] text-ink">Log in</h1>
      <p className="mb-6 text-sm text-muted">Check on your self-hosted n8n workflows.</p>
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
        <label className="text-sm text-muted">
          Password
          <Input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-failing">
            {error}
          </p>
        )}
        <Button type="submit" disabled={submitting}>
          {submitting ? "Logging in..." : "Log in"}
        </Button>
      </form>
      <p className="mt-4 text-sm text-muted">
        <Link href="/forgot-password" className="focus-ring rounded-[2px] text-accent hover:underline">
          Forgot password?
        </Link>
      </p>
      <p className="mt-2 text-sm text-muted">
        Don&apos;t have an account?{" "}
        <Link href="/signup" className="focus-ring rounded-[2px] text-accent hover:underline">
          Sign up
        </Link>
      </p>
    </div>
  );
}
