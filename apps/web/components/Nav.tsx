"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function Nav() {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  async function handleLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <nav className="border-b border-hairline bg-panel px-6 py-3 flex items-center justify-between">
      <Link href="/" className="focus-ring rounded-[4px] font-mono text-sm font-semibold tracking-[0.02em] text-primary">
        Watchdog
      </Link>
      {!loading &&
        (user ? (
          <div className="flex items-center gap-4 text-sm">
            <Link
              href="/account"
              className="focus-ring rounded-[4px] font-mono text-xs text-muted transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent"
            >
              {user.email}
            </Link>
            <button
              onClick={handleLogout}
              className="focus-ring rounded-[4px] cursor-pointer text-ink transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent"
            >
              Log out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-4 text-sm">
            <Link
              href="/login"
              className="focus-ring rounded-[4px] text-ink transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="focus-ring rounded-[4px] text-ink transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent"
            >
              Sign up
            </Link>
          </div>
        ))}
    </nav>
  );
}
