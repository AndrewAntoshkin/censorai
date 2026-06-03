"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthFormShell } from "@/components/auth/auth-form-shell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [registrationCode, setRegistrationCode] = useState("");
  const [orgHint, setOrgHint] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

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

  async function onSubmit(e: FormEvent) {
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
      router.replace("/");
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
    <AuthFormShell
      title="Регистрация"
      subtitle="Введите код организации — он выдаётся администратором"
      footer={
        <>
          Уже есть аккаунт?{" "}
          <Link href="/login" className="text-primary hover:underline">
            Войти
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <label className="text-sm font-medium" htmlFor="code">
            Код организации
          </label>
          <Input
            id="code"
            required
            autoComplete="off"
            placeholder="Например, FRAMECHECK2026"
            value={registrationCode}
            onChange={(e) => {
              setRegistrationCode(e.target.value);
              void checkCode(e.target.value);
            }}
            onBlur={() => void checkCode(registrationCode)}
          />
          {orgHint && (
            <p className="text-xs text-muted-foreground">
              Организация: <span className="font-medium text-foreground">{orgHint}</span>
            </p>
          )}
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium" htmlFor="name">
            Имя
          </label>
          <Input
            id="name"
            required
            autoComplete="name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium" htmlFor="email">
            Email
          </label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="space-y-1.5">
          <label className="text-sm font-medium" htmlFor="password">
            Пароль (мин. 8 символов)
          </label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Button type="submit" className="w-full" disabled={pending}>
          {pending ? "Создание…" : "Создать аккаунт"}
        </Button>
      </form>
    </AuthFormShell>
  );
}
