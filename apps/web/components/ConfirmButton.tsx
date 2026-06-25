"use client";

import { useEffect, useRef, useState } from "react";
import Button from "@/components/Button";

interface ConfirmButtonProps {
  children: React.ReactNode;
  onConfirm: () => void;
  disabled?: boolean;
  pendingLabel: string;
  pending: boolean;
  prompt?: string;
  confirmLabel?: string;
}

const ARM_TIMEOUT_MS = 5000;

/**
 * Inline two-step delete confirmation, replacing the browser-native
 * window.confirm() dialog -- the latter breaks out of the instrument-panel
 * visual language at the one moment (a destructive action) where a
 * deliberate, on-brand UI matters most. Auto-disarms after 5s so an
 * accidental first click can't sit "armed" indefinitely.
 */
export default function ConfirmButton({
  children,
  onConfirm,
  disabled = false,
  pendingLabel,
  pending,
  prompt = "Are you sure?",
  confirmLabel = "Yes, delete",
}: ConfirmButtonProps) {
  const [armed, setArmed] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  function arm() {
    setArmed(true);
    timeoutRef.current = setTimeout(() => setArmed(false), ARM_TIMEOUT_MS);
  }

  function disarm() {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setArmed(false);
  }

  if (!armed) {
    return (
      <Button variant="danger" onClick={arm} disabled={disabled || pending}>
        {pending ? pendingLabel : children}
      </Button>
    );
  }

  return (
    <div className="animate-enter flex flex-wrap items-center gap-3">
      <span className="text-sm text-ink">{prompt}</span>
      <Button
        variant="ghost"
        onClick={disarm}
        disabled={pending}
        className="px-3 py-1.5 text-xs pointer-coarse:min-h-11 pointer-coarse:px-4"
      >
        Cancel
      </Button>
      <Button
        variant="danger"
        onClick={() => {
          disarm();
          onConfirm();
        }}
        disabled={disabled || pending}
        className="px-3 py-1.5 text-xs pointer-coarse:min-h-11 pointer-coarse:px-4"
      >
        {pending ? pendingLabel : confirmLabel}
      </Button>
    </div>
  );
}
