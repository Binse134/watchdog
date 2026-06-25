"use client";

import { useEffect, useRef, useState } from "react";
import type { HealthStatus } from "@/lib/types";

// text-[#0a0a0a] (near-black) is the system default for filled status pills,
// but it measures only 4.16:1 on status-failing -- below the 4.5:1 AA floor
// for this text size (verified against DESIGN.md's oklch tokens; DESIGN.md
// itself flagged this as "confirm contrast per pill, adjust to white if it
// falls short" but it was never actually checked). White on failing measures
// 4.76:1 and passes. Silent's black text measures 4.59:1 and already passes
// -- white on silent would actually be worse (4.31:1), so only failing flips.
const FILL_COLOR: Partial<Record<HealthStatus, string>> = {
  failing: "bg-failing text-white",
  silent: "bg-silent text-[#0a0a0a]",
};

/**
 * The Calm Default Rule (DESIGN.md): only failing/silent render as a
 * filled pill. healthy/unused render as quiet dot+text so a healthy
 * dashboard stays visually calm instead of matching a broken one.
 */
export default function StatusBadge({ status }: { status: HealthStatus }) {
  const fill = FILL_COLOR[status];
  const popping = useStatusChangePop(status);
  const popClass = popping ? "animate-status-pop" : "";

  if (fill) {
    return (
      <span
        className={`inline-flex items-center rounded-full px-2.5 py-0.5 font-mono text-xs font-medium tracking-[0.02em] capitalize ${fill} ${popClass}`}
      >
        {status}
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center gap-1.5 font-mono text-xs capitalize text-muted ${popClass}`}>
      <span
        className={`h-1.5 w-1.5 flex-none rounded-full ${
          status === "healthy" ? "bg-healthy" : "border border-muted"
        }`}
      />
      {status}
    </span>
  );
}

/** True for ~240ms right after `status` changes from a previously-seen value
 * (skips the pop on first mount, so an initial page load stays calm). */
function useStatusChangePop(status: string): boolean {
  const previous = useRef(status);
  const [popping, setPopping] = useState(false);

  useEffect(() => {
    if (previous.current === status) return;
    previous.current = status;
    setPopping(true);
    const timeout = setTimeout(() => setPopping(false), 240);
    return () => clearTimeout(timeout);
  }, [status]);

  return popping;
}
