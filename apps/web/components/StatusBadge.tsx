import type { HealthStatus } from "@/lib/types";

const FILL_COLOR: Partial<Record<HealthStatus, string>> = {
  failing: "bg-failing",
  silent: "bg-silent",
  orphaned: "bg-orphaned",
};

/**
 * The Calm Default Rule (DESIGN.md): only failing/silent/orphaned render as a
 * filled pill. healthy/unused render as quiet dot+text so a healthy
 * dashboard stays visually calm instead of matching a broken one.
 */
export default function StatusBadge({ status }: { status: HealthStatus }) {
  const fill = FILL_COLOR[status];

  if (fill) {
    return (
      <span
        className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-xs font-medium tracking-[0.02em] capitalize text-[#0a0a0a] ${fill}`}
      >
        {status}
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-xs capitalize text-muted">
      <span
        className={`h-1.5 w-1.5 flex-none rounded-full ${
          status === "healthy" ? "bg-healthy" : "border border-muted"
        }`}
      />
      {status}
    </span>
  );
}
