"use client";

import { ArrowRight } from "lucide-react";
import { useLandingAuth } from "@/components/landing/landing-login-host";

export function TryPlacementButton() {
  const { openRegister } = useLandingAuth();

  return (
    <button
      type="button"
      onClick={() => openRegister()}
      className="mt-10 inline-flex w-fit cursor-pointer items-center gap-2 rounded-full border-0 bg-[var(--v7-white)] px-6 py-3 text-sm font-medium text-[var(--v7-ink)] transition-colors hover:bg-[var(--v7-cream)]"
    >
      Попробовать режим
      <ArrowRight className="h-4 w-4" />
    </button>
  );
}
