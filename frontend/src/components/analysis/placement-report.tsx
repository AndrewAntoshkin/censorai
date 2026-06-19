"use client";

import { useCallback } from "react";
import { Copy, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { AnalysisAPI, SceneAPI } from "@/lib/api";

const VISIBILITY_LABELS: Record<string, string> = {
  prominent: "Крупный план",
  background: "Фон",
  partial: "Частично",
  unclear: "Неясно",
};

const SLOT_LABELS: Record<string, string> = {
  replace: "Замена предмета",
  opportunity: "Слот в сцене",
};

const SUITABILITY_LABELS: Record<string, string> = {
  high: "Высокая",
  medium: "Средняя",
  low: "Низкая",
};

function suitabilityStyle(level: string | null | undefined) {
  switch (level) {
    case "high":
      return { badge: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400", dot: "bg-emerald-500" };
    case "medium":
      return { badge: "bg-amber-500/10 text-amber-800 dark:text-amber-400", dot: "bg-amber-500" };
    default:
      return { badge: "bg-muted text-muted-foreground", dot: "bg-muted-foreground" };
  }
}

function TimecodeButton({ start, end }: { start: string | null; end: string | null }) {
  const [copied, setCopied] = useState(false);
  const label = start && end ? `${start} – ${end}` : start || end || "—";

  const copy = useCallback(async () => {
    const text = start || "";
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  }, [start]);

  return (
    <button
      type="button"
      onClick={copy}
      className="group inline-flex items-center gap-1.5 rounded-md bg-accent px-2 py-1 font-mono text-xs text-foreground transition-colors hover:bg-primary/10"
      title="Скопировать таймкод"
    >
      {label}
      {copied ? (
        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
      ) : (
        <Copy className="h-3 w-3 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
      )}
    </button>
  );
}

function PlacementHitCard({ scene }: { scene: SceneAPI }) {
  const style = suitabilityStyle(scene.risk_level);
  return (
    <div className="relative rounded-xl border border-border bg-card p-4">
      <span className={cn("absolute left-0 top-3 bottom-3 w-1 rounded-full", style.dot)} />
      <div className="min-w-0 pl-3">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              #{scene.scene_number}
            </span>
            <TimecodeButton start={scene.start_time} end={scene.end_time} />
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
              style.badge
            )}
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", style.dot)} />
            {SUITABILITY_LABELS[scene.risk_level || ""] || scene.risk_level}
          </span>
        </div>

        {scene.description && (
          <p className="mb-2 text-sm text-foreground">{scene.description}</p>
        )}

        <dl className="grid gap-2 text-sm">
          {scene.reason && (
            <>
              <dt className="text-muted-foreground">В кадре</dt>
              <dd className="text-foreground">{scene.reason}</dd>
            </>
          )}
          {scene.risk && (
            <>
              <dt className="text-muted-foreground">Заметность</dt>
              <dd className="text-foreground">
                {VISIBILITY_LABELS[scene.risk] || scene.risk}
              </dd>
            </>
          )}
          {scene.mode && (
            <>
              <dt className="text-muted-foreground">Тип слота</dt>
              <dd className="text-foreground">
                {SLOT_LABELS[scene.mode] || scene.mode}
              </dd>
            </>
          )}
          {scene.quote && (
            <>
              <dt className="text-muted-foreground">Для монтажа</dt>
              <dd className="text-foreground">{scene.quote}</dd>
            </>
          )}
        </dl>
      </div>
    </div>
  );
}

export function PlacementReportBody({
  analysis,
  summary,
}: {
  analysis: AnalysisAPI;
  summary: NonNullable<AnalysisAPI["summary"]>;
}) {
  const hits = analysis.scenes.filter((s) => s.risk || s.description);

  return (
    <>
      <div className="mb-6 rounded-xl border border-primary/20 bg-primary/5 p-5">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Product placement
        </p>
        <p className="mt-1 text-lg font-semibold text-foreground">
          «{summary.placement_query || "—"}»
        </p>
        <div className="mt-3 flex flex-wrap gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Слотов: </span>
            <span className="font-medium tabular-nums">{summary.total_hits ?? hits.length}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Высокая пригодность: </span>
            <span className="font-medium tabular-nums">
              {summary.high_suitability_count ?? 0}
            </span>
          </div>
        </div>
        <p className="mt-3 text-xs text-muted-foreground">
          Видео не хранится — откройте свой файл и перемотайте по таймкоду (клик копирует).
        </p>
      </div>

      <h3 className="mb-4 text-sm font-semibold text-foreground">
        Места для размещения ({hits.length})
      </h3>

      <div className="space-y-3">
        {hits.map((scene) => (
          <PlacementHitCard key={scene.id} scene={scene} />
        ))}
        {hits.length === 0 && (
          <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
            Подходящих моментов для «{summary.placement_query}» не найдено
          </div>
        )}
      </div>
    </>
  );
}
