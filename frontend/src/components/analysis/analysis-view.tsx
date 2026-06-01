"use client";

import { useEffect, useState } from "react";
import { AppLayout } from "@/components/layout/app-layout";
import { ArrowLeft, Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { riskLevelStyle } from "@/lib/risk";
import { api, type AnalysisAPI, type SceneAPI } from "@/lib/api";
import Link from "next/link";

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

export function AnalysisView({ fileId }: AnalysisViewProps) {
  const [analysis, setAnalysis] = useState<AnalysisAPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    api.files
      .getAnalysis(fileId)
      .then((data) => active && setAnalysis(data))
      .catch((err) => active && setError(err.message))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [fileId]);

  if (loading) {
    return (
      <AppLayout breadcrumb={[{ label: "Главная", href: "/" }, { label: "Загрузка…" }]}>
        <div className="flex h-64 items-center justify-center gap-3 text-sm text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          Загрузка результатов анализа…
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

  return (
    <AppLayout
      breadcrumb={[
        { label: "Главная", href: "/" },
        { label: analysis.video_title || "Результат" },
      ]}
    >
      <div className="mx-auto max-w-6xl">
        <Link
          href="/"
          className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Назад
        </Link>

        <h1 className="mb-1 text-2xl font-semibold tracking-tight text-foreground">
          {analysis.video_title || "Результат анализа"}
        </h1>
        {(analysis.duration || summary) && (
          <p className="mb-7 text-sm text-muted-foreground">
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

        <div className="flex flex-col gap-6 lg:flex-row">
          <aside className="w-full shrink-0 lg:w-80">
            <div className="sticky top-6 space-y-5 rounded-xl border border-border bg-card p-5">
              <h3 className="text-sm font-semibold text-foreground">
                Детали проверки
              </h3>

              {summary && (
                <>
                  {(summary.recommended_age_rating || summary.age_rating_reason) && (
                    <div className="rounded-lg border border-warning/30 bg-warning/5 p-3">
                      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Рекомендация по рейтингу (triage)
                      </p>
                      {summary.recommended_age_rating && (
                        <p className="text-lg font-semibold tabular-nums text-foreground">
                          {summary.recommended_age_rating}
                        </p>
                      )}
                      {summary.age_rating_reason && (
                        <p className="mt-1 text-xs text-muted-foreground">
                          {summary.age_rating_reason}
                        </p>
                      )}
                      <p className="mt-2 text-[11px] text-muted-foreground">
                        Не юридический вердикт — требует проверки редактором
                      </p>
                      {summary.age_rating_triggers &&
                        summary.age_rating_triggers.length > 0 && (
                          <ul className="mt-2 space-y-1 text-xs text-foreground">
                            {summary.age_rating_triggers.map((t, i) => (
                              <li key={i}>
                                Сцена {t.scene_number ?? "?"} ({t.start_time ?? "?"}):{" "}
                                {RISK_LABELS[t.trigger ?? ""] || t.trigger}
                                {t.reason ? ` — ${t.reason}` : ""}
                              </li>
                            ))}
                          </ul>
                        )}
                    </div>
                  )}

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
                                : c.status === "review"
                                  ? "text-primary"
                                  : "text-warning";
                            const dot =
                              c.status === "ok"
                                ? "bg-success"
                                : c.status === "review"
                                  ? "bg-primary"
                                  : "bg-warning";
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
                                    {c.status === "ok"
                                      ? "соответствует"
                                      : c.status === "review"
                                        ? "на проверку"
                                        : "внимание"}
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
                              </li>
                            );
                          })}
                        </ul>
                        <p className="mt-2 text-[11px] text-muted-foreground">
                          Triage-проверка, не юридическое заключение.
                        </p>
                      </div>
                    )}

                  {summary.entities && summary.entities.length > 0 && (
                    <div className="border-t border-border pt-4">
                      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Сущности для проверки по реестрам
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

              <Button
                className="w-full gap-2"
                size="lg"
                onClick={() => {
                  window.open(api.files.getReportUrl(fileId), "_blank");
                }}
              >
                <Download className="h-4 w-4" />
                Скачать отчёт
              </Button>
            </div>
          </aside>

          <div className="min-w-0 flex-1">
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
