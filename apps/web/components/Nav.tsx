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
    <nav className="border-b border-hairline bg-panel px-4 py-3 flex items-center justify-between gap-3 sm:px-6">
      <Link
        href="/"
        className="focus-ring flex-none rounded-[4px] font-mono text-sm font-semibold tracking-[0.02em] text-primary"
      >
        Watchdog
      </Link>
      {!loading &&
        (user ? (
          <div className="flex min-w-0 items-center gap-3 text-sm sm:gap-4">
            <Link
              href="/account"
              className="focus-ring min-w-0 truncate rounded-[4px] py-1.5 font-mono text-xs text-muted transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent pointer-coarse:py-3"
              title={user.email}
            >
              {user.email}
            </Link>
            <button
              onClick={handleLogout}
              className="focus-ring flex-none cursor-pointer rounded-[4px] py-1.5 text-ink transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent pointer-coarse:py-3"
            >
              Log out
            </button>
          </div>
        ) : (
          <div className="flex flex-none items-center gap-3 text-sm sm:gap-4">
            <Link
              href="/login"
              className="focus-ring rounded-[4px] py-1.5 text-ink transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent pointer-coarse:py-3"
            >
              Log in
            </Link>
            <Link
              href="/signup"
              className="focus-ring rounded-[4px] py-1.5 text-ink transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] hover:text-accent pointer-coarse:py-3"
            >
              Sign up
            </Link>
          </div>
        ))}
    </nav>
  );
}
