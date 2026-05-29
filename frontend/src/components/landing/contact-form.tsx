"use client";

import { useState } from "react";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";

export function ContactForm() {
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
      <div className="text-center py-8">
        <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-4" />
        <h3 className="text-xl font-semibold text-white mb-2">
          Заявка отправлена
        </h3>
        <p className="text-gray-400 text-sm">
          Мы свяжемся с вами в ближайшее время
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-sm mx-auto space-y-4">
      <div>
        <input
          type="text"
          required
          placeholder="Контактное лицо"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-white/30"
        />
      </div>
      <div>
        <input
          type="text"
          required
          placeholder="Название организации"
          value={form.company}
          onChange={(e) => setForm({ ...form, company: e.target.value })}
          className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-white/30"
        />
      </div>
      <div>
        <input
          type="email"
          required
          placeholder="Рабочая почта"
          value={form.email}
          onChange={(e) => setForm({ ...form, email: e.target.value })}
          className="w-full px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-white/30"
        />
      </div>
      <label className="flex items-start gap-3 cursor-pointer">
        <input
          type="checkbox"
          required
          checked={form.consent}
          onChange={(e) => setForm({ ...form, consent: e.target.checked })}
          className="mt-0.5 w-4 h-4 rounded border-white/20 bg-white/10 text-blue-500 focus:ring-blue-500/30"
        />
        <span className="text-xs text-gray-400 leading-relaxed">
          Даю согласие на{" "}
          <span className="text-gray-300 underline underline-offset-2">
            обработку персональных данных
          </span>{" "}
          в соответствии с 152-ФЗ
        </span>
      </label>
      <button
        type="submit"
        disabled={status === "loading" || !form.consent}
        className="w-full inline-flex items-center justify-center gap-2 bg-white text-gray-900 px-8 py-3.5 rounded-xl text-sm font-medium hover:bg-gray-100 transition-colors disabled:opacity-70"
      >
        {status === "loading" ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <>
            Оставить заявку
            <ArrowRight className="w-4 h-4" />
          </>
        )}
      </button>
    </form>
  );
}
