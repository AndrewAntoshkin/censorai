"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { AppLayout } from "@/components/layout/app-layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts/auth-context";

export default function ProfilePage() {
  const { user, loading, refresh, logout } = useAuth();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name);
      setEmail(user.email);
    }
  }, [user]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!user) return;
    setError(null);
    setMessage(null);
    setPending(true);
    try {
      const { api } = await import("@/lib/api");
      await api.auth.updateProfile({
        display_name: displayName.trim(),
        email: email.trim(),
      });
      await refresh();
      setMessage("Профиль сохранён");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить");
    } finally {
      setPending(false);
    }
  }

  if (loading) {
    return (
      <AppLayout breadcrumb={[{ label: "Профиль" }]}>
        <p className="text-sm text-muted-foreground">Загрузка…</p>
      </AppLayout>
    );
  }

  if (!user) {
    return (
      <AppLayout breadcrumb={[{ label: "Профиль" }]}>
        <p className="text-sm text-muted-foreground">
          <Link href="/login" className="text-primary hover:underline">
            Войдите
          </Link>
          , чтобы редактировать профиль.
        </p>
      </AppLayout>
    );
  }

  const initials = user.display_name
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <AppLayout breadcrumb={[{ label: "Профиль" }]}>
      <div className="mx-auto max-w-lg">
        <div className="mb-6 flex items-center gap-4">
          <span className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/12 text-lg font-semibold text-primary">
            {initials}
          </span>
          <div>
            <h1 className="text-lg font-semibold">{user.display_name}</h1>
            <p className="text-sm text-muted-foreground">{user.email}</p>
            {(user.active_organization ?? user.organization) && (
              <p className="text-sm text-muted-foreground">
                Организация: {(user.active_organization ?? user.organization)!.name}
                {user.role === "super_admin" && " · супер-админ"}
              </p>
            )}
          </div>
        </div>

        <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-border p-6">
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="displayName">
              Отображаемое имя
            </label>
            <Input
              id="displayName"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              required
            />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-medium" htmlFor="email">
              Email
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          {message && <p className="text-sm text-primary">{message}</p>}
          {error && <p className="text-sm text-destructive">{error}</p>}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" disabled={pending}>
              {pending ? "Сохранение…" : "Сохранить"}
            </Button>
            <Button type="button" variant="outline" onClick={() => void logout()}>
              Выйти
            </Button>
          </div>
        </form>
      </div>
    </AppLayout>
  );
}
