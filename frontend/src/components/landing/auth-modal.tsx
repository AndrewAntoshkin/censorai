"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import { Loader2, X } from "lucide-react";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";

export type AuthModalMode = "login" | "register";

const inputClass =
  "w-full border-b border-[var(--v7-border)] bg-transparent py-3.5 text-sm text-[var(--v7-white-warm)] placeholder:text-[var(--v7-text-faint)] focus:border-[var(--v7-text-muted)] focus:outline-none";

export function AuthModal({
  open,
  onOpenChange,
  mode,
  onModeChange,
  next = "/",
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: AuthModalMode;
  onModeChange: (mode: AuthModalMode) => void;
  next?: string;
}) {
  const { login, register } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [registrationCode, setRegistrationCode] = useState("");
  const [orgHint, setOrgHint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const isLogin = mode === "login";

  useEffect(() => {
    if (open) {
      setError(null);
      setPending(false);
    }
  }, [open]);

  useEffect(() => {
    setError(null);
    setPending(false);
  }, [mode]);

  async function checkCode(raw: string) {
    const code = raw.trim();
    if (code.length < 4) {
      setOrgHint(null);
      return;
    }
    try {
      const res = await api.auth.validateCode(code);
      setOrgHint(res.organization.name);
      setError(null);
    } catch {
      setOrgHint(null);
    }
  }

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await login(email.trim(), password);
      onOpenChange(false);
      router.replace(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось войти");
    } finally {
      setPending(false);
    }
  }

  async function onRegister(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await register(
        email.trim(),
        password,
        displayName.trim(),
        registrationCode.trim()
      );
      onOpenChange(false);
      router.replace(next);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Не удалось зарегистрироваться";
      if (msg.includes("409") || msg.includes("already registered")) {
        setError("Этот email уже зарегистрирован — войдите через «Войти» ниже.");
      } else if (msg.includes("registration code") || msg.includes("Invalid")) {
        setError("Неверный или неактивный код организации");
      } else {
        setError(msg);
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Backdrop className="fixed inset-0 z-[100] bg-black/70 supports-backdrop-filter:backdrop-blur-sm data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0" />
        <DialogPrimitive.Popup className="landing-page fixed left-1/2 top-1/2 z-[100] max-h-[calc(100svh-2rem)] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl border border-[var(--v7-border)] bg-[var(--v7-dark)] text-[var(--v7-white)] shadow-2xl outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95">
          <div className="relative px-7 pb-7 pt-8 sm:px-8 sm:pb-8">
            <DialogPrimitive.Close
              aria-label="Закрыть"
              className="absolute right-4 top-4 rounded-full p-2 text-[var(--v7-text-faint)] transition-colors hover:bg-[var(--v7-border)] hover:text-[var(--v7-white-warm)]"
            >
              <X className="h-4 w-4" />
            </DialogPrimitive.Close>

            <DialogPrimitive.Title className="landing-logo text-[var(--v7-white)]">
              фреймчек
            </DialogPrimitive.Title>
            <p className="mt-6 text-xl font-medium tracking-tight text-[var(--v7-white-warm)]">
              {isLogin ? "Вход" : "Регистрация"}
            </p>
            <p className="mt-1 text-sm text-[var(--v7-text-subtle)]">
              {isLogin
                ? "Вход в кабинет вашей организации"
                : "Введите код организации — он выдаётся администратором"}
            </p>

            {isLogin ? (
              <form onSubmit={onLogin} className="mt-8 space-y-0">
                <input
                  id="landing-auth-email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                />
                <input
                  id="landing-auth-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  placeholder="Пароль"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                />
                {error && (
                  <p className="pt-4 text-sm text-[var(--v7-red-accent)]">{error}</p>
                )}
                <button
                  type="submit"
                  disabled={pending}
                  className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-full bg-[var(--v7-white)] px-8 py-3.5 text-[var(--landing-body)] font-medium text-[var(--v7-ink)] transition-colors hover:bg-[var(--v7-cream)] disabled:opacity-60"
                >
                  {pending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Вход…
                    </>
                  ) : (
                    "Войти"
                  )}
                </button>
              </form>
            ) : (
              <form onSubmit={onRegister} className="mt-8 space-y-0">
                <input
                  id="landing-auth-code"
                  required
                  autoComplete="off"
                  placeholder="Код организации"
                  value={registrationCode}
                  onChange={(e) => {
                    setRegistrationCode(e.target.value);
                    void checkCode(e.target.value);
                  }}
                  onBlur={() => void checkCode(registrationCode)}
                  className={inputClass}
                />
                {orgHint && (
                  <p className="pt-2 text-xs text-[var(--v7-text-subtle)]">
                    Организация:{" "}
                    <span className="font-medium text-[var(--v7-white-warm)]">{orgHint}</span>
                  </p>
                )}
                <input
                  id="landing-auth-name"
                  required
                  autoComplete="name"
                  placeholder="Имя"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className={inputClass}
                />
                <input
                  id="landing-auth-register-email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className={inputClass}
                />
                <input
                  id="landing-auth-register-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  placeholder="Пароль (мин. 8 символов)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className={inputClass}
                />
                {error && (
                  <p className="pt-4 text-sm text-[var(--v7-red-accent)]">{error}</p>
                )}
                <button
                  type="submit"
                  disabled={pending}
                  className="mt-8 inline-flex w-full items-center justify-center gap-2 rounded-full bg-[var(--v7-white)] px-8 py-3.5 text-[var(--landing-body)] font-medium text-[var(--v7-ink)] transition-colors hover:bg-[var(--v7-cream)] disabled:opacity-60"
                >
                  {pending ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Создание…
                    </>
                  ) : (
                    "Создать аккаунт"
                  )}
                </button>
              </form>
            )}

            <p className="mt-6 text-center text-sm text-[var(--v7-text-subtle)]">
              {isLogin ? (
                <>
                  Нет аккаунта?{" "}
                  <button
                    type="button"
                    onClick={() => onModeChange("register")}
                    className="cursor-pointer border-0 bg-transparent p-0 text-[var(--v7-white-warm)] underline-offset-4 hover:underline"
                  >
                    Регистрация
                  </button>
                </>
              ) : (
                <>
                  Уже есть аккаунт?{" "}
                  <button
                    type="button"
                    onClick={() => onModeChange("login")}
                    className="cursor-pointer border-0 bg-transparent p-0 text-[var(--v7-white-warm)] underline-offset-4 hover:underline"
                  >
                    Войти
                  </button>
                </>
              )}
            </p>
          </div>
        </DialogPrimitive.Popup>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
