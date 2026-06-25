"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Persistent across all three connection-scoped pages so a user can jump
 * directly between them (previously alerts/settings only had a "back to
 * workflows" link, with no direct path between alerts <-> settings).
 * DESIGN.md's Navigation section: active section in instrument-blue text,
 * not a filled pill or underline.
 */
export default function ConnectionSubNav({ connectionId }: { connectionId: string }) {
  const pathname = usePathname();
  const tabs = [
    { href: `/connections/${connectionId}`, label: "Workflows" },
    { href: `/connections/${connectionId}/alerts`, label: "Alerts" },
    { href: `/connections/${connectionId}/settings`, label: "Settings" },
  ];

  return (
    <nav className="mb-6 flex items-center gap-5 border-b border-hairline pb-3 text-sm">
      {tabs.map((tab) => {
        const active = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`focus-ring rounded-[4px] py-1.5 font-mono text-xs tracking-[0.02em] transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] pointer-coarse:py-3 ${
              active ? "text-accent" : "text-muted hover:text-ink"
            }`}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
