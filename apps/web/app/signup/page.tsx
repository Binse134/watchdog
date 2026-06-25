"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import type { User } from "@/lib/types";
import Button from "@/components/Button";
import Input from "@/components/Input";

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { refresh } = useAuth();
  const router = useRouter();

  useEffect(() => {
    document.title = "Sign up · Watchdog";
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.post<User>("/auth/signup", { email, password });
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
      <h1 className="mb-1 text-2xl font-semibold tracking-[-0.01em] text-ink">Sign up</h1>
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
            minLength={8}
            autoComplete="new-password"
            placeholder="Min 8 characters"
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
          {submitting ? "Creating account..." : "Sign up"}
        </Button>
      </form>
      <p className="mt-4 text-sm text-muted">
        Already have an account?{" "}
        <Link href="/login" className="focus-ring rounded-[2px] text-accent hover:underline">
          Log in
        </Link>
      </p>
    </div>
  );
}
