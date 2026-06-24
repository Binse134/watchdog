import type { HTMLAttributes } from "react";

export default function Card({ className = "", ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`rounded-[10px] border border-hairline bg-panel p-6 ${className}`} />;
}
