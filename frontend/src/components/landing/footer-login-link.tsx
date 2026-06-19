"use client";

import { useLandingAuth } from "@/components/landing/landing-login-host";

export function FooterLoginLink() {
  const { openLogin } = useLandingAuth();

  return (
    <button
      type="button"
      onClick={() => openLogin()}
      className="cursor-pointer border-0 bg-transparent p-0 text-sm text-[var(--v7-text-subtle)] transition-colors hover:text-[var(--v7-white-warm)]"
    >
      Войти
    </button>
  );
}
