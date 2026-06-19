"use client";

import Link from "next/link";
import { useLandingAuth } from "@/components/landing/landing-login-host";

const NAV_LINKS = [
  { href: "#workflows", label: "Сценарии" },
  { href: "#platform", label: "Платформа" },
  { href: "#categories", label: "Категории" },
  { href: "#placement", label: "Плейсмент" },
  { href: "#proof", label: "Результаты" },
  { href: "#pricing", label: "Стоимость" },
];

function Logo() {
  return <span className="landing-logo text-[var(--v7-white)]">фреймчек</span>;
}

export function LandingNav() {
  const { openLogin } = useLandingAuth();

  return (
    <header className="landing-header fixed top-0 left-0 right-0 z-50">
      <nav className="landing-header-main">
        <div className="landing-header-inner">
          <Link href="/landing" className="shrink-0">
            <Logo />
          </Link>
          <div className="landing-nav-links">
            {NAV_LINKS.map((link) => (
              <a key={link.href} href={link.href} className="landing-nav-link">
                {link.label}
              </a>
            ))}
          </div>
          <div className="landing-nav-actions">
            <button
              type="button"
              onClick={() => openLogin()}
              className="landing-nav-link hidden cursor-pointer border-0 bg-transparent p-0 sm:inline"
            >
              Войти
            </button>
            <a href="#cta" className="landing-nav-cta">
              Оставить заявку
            </a>
          </div>
        </div>
      </nav>
    </header>
  );
}
