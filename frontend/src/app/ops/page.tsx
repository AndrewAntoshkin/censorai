"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

type OpsMetrics = {
  video_provider: string;
  object_storage: boolean;
  cascade_enabled: boolean;
  worker_poll_seconds: number;
  videos_by_status: Record<string, number>;
  jobs_by_status: Record<string, number>;
  analyzing_count: number;
  queued_jobs: number;
  failed_jobs: number;
  stale_analyzing: number;
  max_job_attempts: number;
};

export default function OpsPage() {
  const { user, loading: authLoading } = useAuth();
  const [metrics, setMetrics] = useState<OpsMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading || !user) return;
    if (user.role !== "super_admin") return;

    api.ops
      .metrics()
      .then(setMetrics)
      .catch((e: Error) => setError(e.message));
  }, [user, authLoading]);

  if (authLoading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user || user.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-lg p-8">
        <h1 className="text-lg font-semibold">Операции</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Доступ только для супер-админа.
        </p>
        <Link href="/" className="mt-4 inline-block text-sm text-primary hover:underline">
          На главную
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="text-xl font-semibold">Операции</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Сводка очереди анализа и конфигурации воркера
      </p>

      {error && (
        <p className="mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}

      {!metrics && !error && (
        <div className="mt-8 flex justify-center">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {metrics && (
        <div className="mt-8 space-y-6">
          <section className="grid gap-3 sm:grid-cols-2">
            <Stat label="Провайдер видео" value={metrics.video_provider} />
            <Stat
              label="Object storage"
              value={metrics.object_storage ? "включён" : "выкл."}
            />
            <Stat label="В анализе" value={String(metrics.analyzing_count)} />
            <Stat label="В очереди (jobs)" value={String(metrics.queued_jobs)} />
            <Stat label="Stale analyzing" value={String(metrics.stale_analyzing)} />
            <Stat label="Ошибки jobs" value={String(metrics.failed_jobs)} />
            <Stat
              label="Poll интервал"
              value={`${metrics.worker_poll_seconds} с`}
            />
            <Stat
              label="Cascade (сцены)"
              value={metrics.cascade_enabled ? "да" : "нет"}
            />
          </section>

          <section>
            <h2 className="text-sm font-medium">Видео по статусу</h2>
            <ul className="mt-2 space-y-1 text-sm">
              {Object.entries(metrics.videos_by_status).map(([k, v]) => (
                <li key={k} className="flex justify-between border-b border-border/50 py-1">
                  <span className="text-muted-foreground">{k}</span>
                  <span className="tabular-nums">{v}</span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h2 className="text-sm font-medium">Jobs по статусу</h2>
            <ul className="mt-2 space-y-1 text-sm">
              {Object.entries(metrics.jobs_by_status).map(([k, v]) => (
                <li key={k} className="flex justify-between border-b border-border/50 py-1">
                  <span className="text-muted-foreground">{k}</span>
                  <span className="tabular-nums">{v}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="mt-1 text-sm font-medium">{value}</div>
    </div>
  );
}
