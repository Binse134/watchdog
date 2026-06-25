import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost" | "danger";

const VARIANT_STYLES: Record<Variant, string> = {
  primary: "bg-primary text-[#0a0a0a] hover:bg-primary-hover",
  ghost: "bg-transparent text-ink border border-hairline hover:border-accent",
  danger: "bg-failing text-[#0a0a0a] hover:opacity-90",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export default function Button({ variant = "primary", className = "", ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={`focus-ring inline-flex items-center justify-center gap-2 rounded-[6px] px-[18px] py-2.5 font-mono text-[13px] font-medium tracking-[0.02em] transition-[background-color,color,transform] duration-150 [transition-timing-function:var(--ease-out-expo)] active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 cursor-pointer ${VARIANT_STYLES[variant]} ${className}`}
    />
  );
}
