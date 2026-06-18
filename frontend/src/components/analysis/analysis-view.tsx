"use client";

import { useEffect, useState } from "react";
import { AppLayout } from "@/components/layout/app-layout";
import { ArrowLeft, Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { riskLevelStyle } from "@/lib/risk";
import { api, type AnalysisAPI, type SceneAPI } from "@/lib/api";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";

const RISK_LABELS: Record<string, string> = {
  drugs: "Наркотики",
  weapons: "Оружие",
  violence: "Насилие",
  sexual_content: "Сексуальный контент",
  profanity: "Нецензурная лексика",
  illegal_actions: "Незаконные действия",
  alcohol: "Алкоголь",
  smoking: "Курение",
  animal_cruelty: "Жестокое обращение с животными",
  forbidden_symbols: "Запрещённая символика",
  text_in_frame: "Текст в кадре",
  extremism: "Экстремизм",
  discreditation_values: "Дискредитация ценностей",
  propaganda: "Пропаганда",
  crime_glorification: "Героизация преступлений",
  excessive_cruelty: "Чрезмерная жестокость",
  suicide: "Суицид",
  minor_content: "Вовлечение несовершеннолетних",
  lgbt_propaganda: "Пропаганда ЛГБТ",
  foreign_agent: "Иноагент (проверка)",
  pedophilia: "Педофилия",
};

const MODE_LABELS: Record<string, string> = {
  depiction: "показ",
  instruction: "инструкция",
  propaganda: "пропаганда",
  general: "общее",
  armed_forces: "ВС РФ",
  glorification: "героизация",
  mention: "упоминание",
  citation: "цитирование",
  logo: "логотип",
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  person: "Лицо",
  organization: "Организация",
  media: "СМИ",
  channel: "Канал",
  logo: "Логотип",
  url: "URL",
  handle: "Ник",
};

const LEVEL_LABELS: Record<string, string> = {
  critical: "Критично",
  warning: "Возможны проблемы",
  info: "Некритично",
};

const REC_LABELS: Record<string, string> = {
  remove: "Вырезать",
  shorten: "Сократить",
  mute: "Заглушить",
  blur: "Размыть",
  edit: "Отредактировать",
  mark: "Добавить маркировку",
  info: "Информирование",
};

function RiskLevelBadge({ level }: { level: string }) {
  const style = riskLevelStyle(level);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
        style.badge
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", style.dot)} />
      {LEVEL_LABELS[level] || level}
    </span>
  );
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-sm text-foreground">{children}</dd>
    </>
  );
}

function AgeRatingRecommendation({
  summary,
}: {
  summary: NonNullable<AnalysisAPI["summary"]>;
}) {
  if (!summary.recommended_age_rating && !summary.age_rating_reason) {
    return null;
  }

  return (
    <div className="mb-6 rounded-xl border border-warning/30 bg-warning/5 p-5">
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
        Рекомендация по рейтингу (triage)
      </p>
      {summary.recommended_age_rating && (
        <p className="text-2xl font-semibold tabular-nums text-foreground">
          {summary.recommended_age_rating}
        </p>
      )}
      {summary.age_rating_reason && (
        <p className="mt-2 text-sm text-foreground">{summary.age_rating_reason}</p>
      )}
      <p className="mt-3 text-xs text-muted-foreground">
        Не юридический вердикт — требует проверки редактором
      </p>
      {summary.age_rating_triggers && summary.age_rating_triggers.length > 0 && (
        <ul className="mt-4 space-y-2 border-t border-warning/20 pt-4 text-sm text-foreground">
          {summary.age_rating_triggers.map((t, i) => (
            <li key={i}>
              <span className="font-medium">
                Сцена {t.scene_number ?? "?"} ({t.start_time ?? "?"}):
              </span>{" "}
              {RISK_LABELS[t.trigger ?? ""] || t.trigger}
              {t.reason ? ` — ${t.reason}` : ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SceneCard({ scene }: { scene: SceneAPI }) {
  const accent = scene.risk_level ? riskLevelStyle(scene.risk_level) : null;
  return (
    <div className="relative rounded-xl border border-border bg-card p-4">
      {accent && (
        <span className={cn("absolute left-0 top-3 bottom-3 w-1 rounded-full", accent.bar)} />
      )}
      <div className={cn("min-w-0", accent && "pl-3")}>
        <div className="mb-3 flex items-start justify-between gap-4">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Сцена {scene.scene_number}
          </span>
          {scene.risk_level && <RiskLevelBadge level={scene.risk_level} />}
        </div>

        <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2">
          <DetailRow label="Таймкод">
            <span className="tabular-nums">
              {scene.start_time || "?"} – {scene.end_time || "?"}
            </span>
          </DetailRow>

          {scene.risk && (
            <DetailRow label="Тип нарушения">
              {RISK_LABELS[scene.risk] || scene.risk}
              {scene.mode && (
                <span className="ml-1.5 text-muted-foreground">
                  ({MODE_LABELS[scene.mode] || scene.mode})
                </span>
              )}
            </DetailRow>
          )}

          {scene.quote && (
            <DetailRow label="Фрагмент диалога">
              <span className="italic text-muted-foreground">«{scene.quote}»</span>
            </DetailRow>
          )}

          <DetailRow label="Описание сцены">{scene.description || "—"}</DetailRow>

          {scene.text_in_frame && (
            <DetailRow label="Текст в кадре">{scene.text_in_frame}</DetailRow>
          )}

          {scene.recommendation && (
            <DetailRow label="Рекомендация">
              <span className="inline-flex items-center rounded-md bg-accent px-2 py-0.5 text-xs font-medium text-foreground">
                {REC_LABELS[scene.recommendation] || scene.recommendation}
              </span>
            </DetailRow>
          )}

          {scene.probability !== null && (
            <DetailRow label="Вероятность">
              <span className="tabular-nums">
                {Math.round(scene.probability * 100)}%
              </span>
            </DetailRow>
          )}

          {scene.reason && <DetailRow label="Основание">{scene.reason}</DetailRow>}
        </dl>
      </div>
    </div>
  );
}

interface AnalysisViewProps {
  fileId: string;
}

function parseDurationSeconds(value: string | null | undefined): number | null {
  if (!value) return null;
  const parts = value.trim().split(":");
  if (parts.length === 2) {
    return Number(parts[0]) * 60 + Number(parts[1]);
  }
  if (parts.length === 3) {
    return Number(parts[0]) * 3600 + Number(parts[1]) * 60 + Number(parts[2]);
  }
  return null;
}

function maxSceneEndSeconds(scenes: SceneAPI[]): number {
  let last = 0;
  for (const scene of scenes) {
    for (const value of [scene.end_time, scene.start_time]) {
      const sec = parseDurationSeconds(value);
      if (sec !== null) last = Math.max(last, sec);
    }
  }
  return last;
}

function coverageMeetsFileLength(
  analysis: AnalysisAPI,
  fileDurationSeconds: number | null
): boolean {
  if (!fileDurationSeconds || fileDurationSeconds <= 30) return false;
  const threshold = Math.max(fileDurationSeconds * 0.82, fileDurationSeconds - 30);
  const reported = parseDurationSeconds(analysis.duration);
  const lastEnd = maxSceneEndSeconds(analysis.scenes);
  if (reported !== null && reported >= threshold) return true;
  if (lastEnd > 0 && lastEnd >= threshold) return true;
  return false;
}

function looksIncomplete(
  summary: AnalysisAPI["summary"],
  analysis: AnalysisAPI,
  fileDurationSeconds: number | null
): boolean {
  const title = (analysis.video_title || "").toLowerCase();
  if (title.includes("фрагмент")) return true;

  if (!summary?.incomplete_coverage) return false;

  // Suppress stale false positives saved before the duration-based fix
  // (high-bitrate shorts flagged only by file size).
  if (coverageMeetsFileLength(analysis, fileDurationSeconds)) return false;

  return true;
}

function IncompleteCoverageBanner({
  note,
  onRetry,
  retrying,
}: {
  note: string;
  onRetry: () => void;
  retrying: boolean;
}) {
  return (
    <div className="mb-6 rounded-xl border border-critical/40 bg-critical/5 p-4">
      <p className="text-sm font-medium text-critical">Неполный анализ</p>
      <p className="mt-1 text-sm text-foreground">{note}</p>
      <Button className="mt-3" size="sm" disabled={retrying} onClick={onRetry}>
        {retrying ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Перезапуск…
          </>
        ) : (
          "Перезапустить анализ"
        )}
      </Button>
    </div>
  );
}

export function AnalysisView({ fileId }: AnalysisViewProps) {
  const [analysis, setAnalysis] = useState<AnalysisAPI | null>(null);
  const [fileDurationSeconds, setFileDurationSeconds] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([api.files.getAnalysis(fileId), api.files.get(fileId)])
      .then(([data, file]) => {
        if (!active) return;
        setAnalysis(data);
        setFileDurationSeconds(file.duration_seconds ?? null);
      })
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [fileId]);

  const handleRetryAnalysis = async () => {
    setRetrying(true);
    setError(null);
    try {
      await api.files.analyze(fileId, { force: true });
      const deadline = Date.now() + 60 * 60 * 1000;
      while (Date.now() < deadline) {
        await new Promise((r) => setTimeout(r, 10000));
        const file = await api.files.get(fileId);
        if (file.status === "analyzed") {
          const data = await api.files.getAnalysis(fileId);
          setAnalysis(data);
          return;
        }
        if (file.status === "error") {
          throw new Error("Анализ завершился с ошибкой");
        }
      }
      throw new Error("Превышено время ожидания анализа");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось перезапустить анализ");
    } finally {
      setRetrying(false);
    }
  };

  if (loading) {
    return (
      <AppLayout breadcrumb={[{ label: "Главная", href: "/" }, { label: "Загрузка…" }]}>
        <div className="mx-auto max-w-6xl space-y-6">
          <div>
            <Skeleton className="mb-3 h-5 w-20" />
            <Skeleton className="h-9 w-96 max-w-full" />
            <Skeleton className="mt-2 h-4 w-64" />
          </div>
          <div className="flex flex-col gap-6 lg:flex-row">
            <div className="w-full lg:w-80">
              <div className="rounded-xl border border-border bg-card p-4">
                <Skeleton className="mb-3 h-4 w-28" />
                <div className="space-y-2">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </div>
              </div>
            </div>
            <div className="min-w-0 flex-1 space-y-3">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-border bg-card p-4">
                  <Skeleton className="mb-3 h-4 w-24" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="mt-2 h-4 w-5/6" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (error || !analysis) {
    return (
      <AppLayout breadcrumb={[{ label: "Главная", href: "/" }, { label: "Ошибка" }]}>
        <div className="flex h-64 items-center justify-center text-sm text-critical">
          Не удалось загрузить результат: {error}
        </div>
      </AppLayout>
    );
  }

  const violationScenes = analysis.scenes.filter((s) => s.risk);
  const summary = analysis.summary;
  const incomplete = looksIncomplete(summary, analysis, fileDurationSeconds);
  const foreignAgentHits =
    summary?.registry_verifications?.filter(
      (v) => v.registry_status === "in_registry" && v.registry === "foreign_agents"
    ) ?? [];

  return (
    <AppLayout
      splitScroll
      breadcrumb={[
        { label: "Главная", href: "/" },
        { label: analysis.video_title || "Результат" },
      ]}
    >
      <div className="mx-auto flex h-full min-h-0 max-w-6xl flex-col overflow-y-auto lg:overflow-hidden">
        <div className="shrink-0">
          <Link
            href="/reports"
            className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Назад
          </Link>

          <div className="mb-1 flex items-start justify-between gap-4">
            <h1 className="min-w-0 text-2xl font-semibold tracking-tight text-foreground">
              {analysis.video_title || "Результат анализа"}
            </h1>
            <Button
              className="shrink-0 gap-2 bg-black text-white hover:bg-neutral-800"
              size="lg"
              onClick={() => {
                window.open(api.files.getReportUrl(fileId), "_blank");
              }}
            >
              <Download className="h-4 w-4" />
              Скачать отчёт
            </Button>
          </div>
          {(analysis.duration || summary) && (
            <p className="mb-6 text-sm text-muted-foreground">
              {[
                analysis.duration,
                summary ? `${summary.risky_scenes} нарушений из ${summary.total_scenes} сцен` : null,
                analysis.analyzed_at
                  ? `проверено ${new Date(analysis.analyzed_at).toLocaleDateString("ru-RU")}`
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </div>

        <div className="flex flex-col gap-12 lg:min-h-0 lg:flex-1 lg:flex-row">
          <aside className="w-full shrink-0 lg:flex lg:w-80 lg:min-h-0 lg:flex-col">
            <div className="space-y-5 lg:min-h-0 lg:flex-1 lg:overflow-y-auto lg:scrollbar-hidden lg:pr-1">
              <h3 className="text-sm font-semibold text-foreground">
                Детали проверки
              </h3>

              {summary && (
                <>
                  {summary.compliance_checks &&
                    summary.compliance_checks.length > 0 && (
                      <div className="border-t border-border pt-4">
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          Нормативная проверка (РФ, 2026)
                        </p>
                        <ul className="space-y-1.5">
                          {summary.compliance_checks.map((c, i) => {
                            const tone =
                              c.status === "ok"
                                ? "text-success"
                                : c.status === "violation"
                                  ? "text-critical"
                                  : c.status === "expertise"
                                    ? "text-primary"
                                    : c.status === "review"
                                      ? "text-primary"
                                      : "text-warning";
                            const dot =
                              c.status === "ok"
                                ? "bg-success"
                                : c.status === "violation"
                                  ? "bg-critical"
                                  : c.status === "expertise"
                                    ? "bg-primary"
                                    : c.status === "review"
                                      ? "bg-primary"
                                      : "bg-warning";
                            const statusLabel =
                              c.status === "ok"
                                ? "соответствует"
                                : c.status === "violation"
                                  ? "нарушение"
                                  : c.status === "expertise"
                                    ? "экспертиза"
                                    : c.status === "review"
                                      ? "на проверку"
                                      : "внимание";
                            return (
                              <li
                                key={i}
                                className="rounded-md border border-border bg-card p-2"
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <span className="text-xs font-semibold text-foreground">
                                    {c.law}
                                  </span>
                                  <span
                                    className={`flex items-center gap-1 text-[11px] font-medium ${tone}`}
                                  >
                                    <span
                                      className={`inline-block h-1.5 w-1.5 rounded-full ${dot}`}
                                    />
                                    {statusLabel}
                                    {c.findings_count > 0 ? ` · ${c.findings_count}` : ""}
                                  </span>
                                </div>
                                <p className="mt-0.5 text-[11px] text-muted-foreground">
                                  {c.title}
                                </p>
                                {c.note && (
                                  <p className="mt-0.5 text-[11px] text-foreground/80">
                                    {c.note}
                                  </p>
                                )}
                                {c.articles && c.articles.length > 0 && (
                                  <p className="mt-0.5 text-[10px] text-muted-foreground">
                                    {c.articles.join(" · ")}
                                  </p>
                                )}
                              </li>
                            );
                          })}
                        </ul>
                        <p className="mt-2 text-[11px] text-muted-foreground">
                          {summary.legal_disclaimer ||
                            "Triage-проверка, не юридическое заключение."}
                        </p>
                      </div>
                    )}

                  {summary.registry_verifications &&
                    summary.registry_verifications.length > 0 && (
                      <div className="border-t border-border pt-4">
                        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          Сверка с реестрами Минюста
                        </p>
                        <ul className="space-y-2 text-xs">
                          {summary.registry_verifications.map((v, i) => (
                            <li
                              key={i}
                              className={cn(
                                "rounded-md border p-2",
                                v.severity === "violation"
                                  ? "border-critical/40 bg-critical/5"
                                  : v.registry_status === "in_registry"
                                    ? "border-warning/40 bg-warning/5"
                                    : "border-border bg-card"
                              )}
                            >
                              <div className="font-medium text-foreground">{v.name}</div>
                              <div className="mt-0.5 text-muted-foreground">
                                {v.registry_status === "in_registry"
                                  ? `В реестре: ${v.matched_registry_name}`
                                  : v.registry_status === "not_in_registry"
                                    ? "Не найден в загруженных реестрах"
                                    : "Реестр недоступен"}
                              </div>
                              {v.article && (
                                <div className="mt-0.5 text-foreground/80">{v.article}</div>
                              )}
                              {v.required_marking && (
                                <div className="mt-1 text-[10px] text-foreground/90">
                                  Маркировка: «{v.required_marking}»
                                  {v.marking_found === false && (
                                    <span className="text-critical"> — не обнаружена в видео</span>
                                  )}
                                </div>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                  <div className="border-t border-border pt-4">
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Иноагенты (Минюст)
                    </p>
                    {foreignAgentHits.length > 0 ? (
                      <ul className="space-y-1.5 text-xs">
                        {foreignAgentHits.map((hit, i) => (
                          <li key={i} className="text-foreground">
                            <span className="font-medium">{hit.matched_registry_name}</span>
                            {hit.name && hit.name !== hit.matched_registry_name && (
                              <span className="text-muted-foreground"> — в кадре: {hit.name}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-success">Реальных совпадений не найдено</p>
                    )}
                  </div>

                  {summary.entities && summary.entities.length > 0 && (
                    <div className="border-t border-border pt-4">
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Сущности в кадре
                      </p>
                      <ul className="space-y-1.5 text-xs">
                        {summary.entities.map((e, i) => (
                          <li key={i} className="text-foreground">
                            <span className="font-medium">{e.name}</span>
                            {e.type && (
                              <span className="text-muted-foreground">
                                {" "}
                                ({ENTITY_TYPE_LABELS[e.type] || e.type})
                              </span>
                            )}
                            {e.context && (
                              <span className="text-muted-foreground"> — {e.context}</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div>
                    <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Вероятность нарушений
                    </p>
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              "h-2 w-2 rounded-full",
                              riskLevelStyle("critical").dot
                            )}
                          />
                          <span className="text-sm text-foreground">Критично</span>
                        </div>
                        <span className="text-sm font-semibold tabular-nums text-foreground">
                          {summary.critical_count}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              "h-2 w-2 rounded-full",
                              riskLevelStyle("warning").dot
                            )}
                          />
                          <span className="text-sm text-foreground">
                            Возможны проблемы
                          </span>
                        </div>
                        <span className="text-sm font-semibold tabular-nums text-foreground">
                          {summary.warning_count}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 border-t border-border pt-4 text-sm">
                    <div>
                      <p className="text-muted-foreground">Всего сцен</p>
                      <p className="font-medium tabular-nums text-foreground">
                        {summary.total_scenes}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground">С рисками</p>
                      <p className="font-medium tabular-nums text-foreground">
                        {summary.risky_scenes}
                      </p>
                    </div>
                  </div>

                  {Object.keys(summary.risk_categories).length > 0 && (
                    <div className="border-t border-border pt-4">
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Категории рисков
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {Object.entries(summary.risk_categories).map(([cat, count]) => (
                          <span
                            key={cat}
                            className="rounded-md bg-accent px-2 py-0.5 text-xs text-foreground"
                          >
                            {RISK_LABELS[cat] || cat} ({count})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

            </div>
          </aside>

          <div className="min-w-0 flex-1 lg:min-h-0 lg:overflow-y-auto lg:scrollbar-hidden">
            {incomplete && (
              <IncompleteCoverageBanner
                note={
                  summary?.incomplete_coverage_note ||
                  "Похоже, проанализировано только начало видео (модель пометила результат как «фрагмент»). Перезапустите анализ — сейчас включён полный лимит ответа."
                }
                onRetry={handleRetryAnalysis}
                retrying={retrying}
              />
            )}
            {summary && <AgeRatingRecommendation summary={summary} />}

            <h3 className="mb-4 text-sm font-semibold text-foreground">
              Нарушения ({violationScenes.length})
            </h3>

            <div className="space-y-3">
              {violationScenes.map((scene) => (
                <SceneCard key={scene.id} scene={scene} />
              ))}
              {violationScenes.length === 0 && (
                <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
                  Нарушений не обнаружено
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
