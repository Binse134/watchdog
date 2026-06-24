import type { InputHTMLAttributes } from "react";

export default function Input({ className = "", ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`focus-ring w-full rounded-[6px] border border-hairline bg-panel-raised px-3 py-2.5 text-[15px] text-ink placeholder:text-muted transition-colors duration-150 [transition-timing-function:var(--ease-out-expo)] focus:border-accent ${className}`}
    />
  );
}
