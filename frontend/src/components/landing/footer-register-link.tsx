"use client";

import { useLandingAuth } from "@/components/landing/landing-login-host";

export function FooterRegisterLink() {
  const { openRegister } = useLandingAuth();

  return (
    <button
      type="button"
      onClick={() => openRegister()}
      className="cursor-pointer border-0 bg-transparent p-0 text-sm text-[var(--v7-text-subtle)] transition-colors hover:text-[var(--v7-white-warm)]"
    >
      Регистрация
    </button>
  );
}
