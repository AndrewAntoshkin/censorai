"use client";

import { useState } from "react";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";

export function ContactForm({ className = "" }: { className?: string }) {
  const [form, setForm] = useState({ email: "", company: "", name: "", consent: false });
  const [status, setStatus] = useState<"idle" | "loading" | "success">("idle");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.consent) return;
    setStatus("loading");
    setTimeout(() => setStatus("success"), 1200);
  };

  if (status === "success") {
    return (
      <div className={`py-10 ${className}`}>
        <CheckCircle2 className="mb-4 h-10 w-10 text-[var(--v7-orange-soft)]" />
        <h3 className="mb-2 text-xl font-medium text-[var(--v7-white-warm)]">Заявка отправлена</h3>
        <p className="text-sm text-[var(--v7-text-subtle)]">Мы свяжемся с вами в ближайшее время</p>
      </div>
    );
  }

  const inputClass =
    "w-full border-b border-[var(--v7-border)] bg-transparent py-3.5 text-sm text-[var(--v7-white-warm)] placeholder:text-[var(--v7-text-faint)] focus:border-[var(--v7-text-muted)] focus:outline-none";

  return (
    <form onSubmit={handleSubmit} className={`w-full space-y-0 ${className}`}>
      <input
        type="text"
        required
        placeholder="Контактное лицо"
        value={form.name}
        onChange={(e) => setForm({ ...form, name: e.target.value })}
        className={inputClass}
      />
      <input
        type="text"
        required
        placeholder="Название организации"
        value={form.company}
        onChange={(e) => setForm({ ...form, company: e.target.value })}
        className={inputClass}
      />
      <input
        type="email"
        required
        placeholder="Рабочая почта"
        value={form.email}
        onChange={(e) => setForm({ ...form, email: e.target.value })}
        className={inputClass}
      />
      <label className="flex cursor-pointer items-start gap-3 border-b border-[var(--v7-border)] py-4">
        <input
          type="checkbox"
          required
          checked={form.consent}
          onChange={(e) => setForm({ ...form, consent: e.target.checked })}
          className="mt-0.5 h-4 w-4 rounded border-[var(--v7-border)] bg-transparent text-[var(--v7-orange)] focus:ring-[var(--v7-orange)]/30"
        />
        <span className="text-xs leading-relaxed text-[var(--v7-text-subtle)]">
          Даю согласие на{" "}
          <span className="text-[var(--v7-text-muted)] underline underline-offset-2">
            обработку персональных данных
          </span>{" "}
          в соответствии с 152-ФЗ
        </span>
      </label>
      <button
        type="submit"
        disabled={status === "loading" || !form.consent}
        className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-full bg-[var(--v7-white)] px-8 py-3.5 text-sm font-medium text-[var(--v7-ink)] transition-colors hover:bg-[var(--v7-cream)] disabled:opacity-70 sm:w-auto"
      >
        {status === "loading" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <>
            Оставить заявку
            <ArrowRight className="h-4 w-4" />
          </>
        )}
      </button>
    </form>
  );
}
