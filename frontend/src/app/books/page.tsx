"use client";

import { useCallback, useState } from "react";
import { AppLayout } from "@/components/layout/app-layout";
import { useDropzone } from "react-dropzone";
import {
  Upload,
  FileText,
  Loader2,
  CheckCircle,
  AlertCircle,
  Download,
  BookOpen,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { riskLevelStyle } from "@/lib/risk";
import { getApiBase } from "@/lib/api";

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
  extremism: "Экстремизм",
  discreditation_values: "Дискредитация ценностей",
  propaganda: "Пропаганда",
  crime_glorification: "Героизация преступлений",
  excessive_cruelty: "Чрезмерная жестокость",
  suicide: "Суицид",
  minor_content: "Вовлечение несовершеннолетних",
};

const LEVEL_LABELS: Record<string, string> = {
  critical: "Критично",
  warning: "Предупреждение",
  info: "Информация",
};

const REC_LABELS: Record<string, string> = {
  remove: "Удалить фрагмент",
  edit: "Отредактировать",
  mark: "Добавить маркировку",
  shorten: "Сократить",
  mute: "Заглушить",
  blur: "Размыть",
};

interface SceneData {
  id: string;
  scene_number: number;
  start_time: string | null;
  end_time: string | null;
  description: string | null;
  risk: string | null;
  risk_level: string | null;
  probability: number | null;
  reason: string | null;
  quote: string | null;
  text_in_frame: string | null;
  recommendation: string | null;
}

interface AnalysisData {
  id: string;
  video_title: string | null;
  duration: string | null;
  analyzed_at: string | null;
  summary: {
    total_scenes: number;
    risky_scenes: number;
    risk_categories: Record<string, number>;
    critical_count: number;
    warning_count: number;
  } | null;
  status: string;
  scenes: SceneData[];
}

type UploadStatus = "idle" | "uploading" | "analyzing" | "done" | "error";

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

function FragmentCard({ scene }: { scene: SceneData }) {
  const [expanded, setExpanded] = useState(true);
  const accent = scene.risk_level ? riskLevelStyle(scene.risk_level) : null;

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-4 p-4 text-left transition-colors hover:bg-accent"
      >
        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-primary/10">
          <BookOpen className="h-5 w-5 text-primary" />
          {accent && (
            <span className={cn("absolute left-0 top-0 h-full w-1", accent.bar)} />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium text-foreground">
              Фрагмент {scene.scene_number}
            </span>
            {scene.start_time && (
              <span className="text-xs tabular-nums text-muted-foreground">
                {scene.start_time}
                {scene.end_time && scene.end_time !== scene.start_time
                  ? ` — ${scene.end_time}`
                  : ""}
              </span>
            )}
            {scene.risk_level && <RiskLevelBadge level={scene.risk_level} />}
          </div>
          <p className="mt-0.5 truncate text-sm text-muted-foreground">
            {scene.description || "—"}
          </p>
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-border px-4 pb-4 pt-4">
          <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2 text-sm">
            {scene.start_time && (
              <>
                <dt className="text-muted-foreground">Расположение</dt>
                <dd className="tabular-nums text-foreground">
                  {scene.start_time}
                  {scene.end_time && scene.end_time !== scene.start_time
                    ? ` — ${scene.end_time}`
                    : ""}
                </dd>
              </>
            )}

            <dt className="text-muted-foreground">Описание</dt>
            <dd className="text-foreground">{scene.description || "—"}</dd>

            {scene.risk && (
              <>
                <dt className="text-muted-foreground">Тип нарушения</dt>
                <dd className="text-foreground">
                  {RISK_LABELS[scene.risk] || scene.risk}
                </dd>
              </>
            )}

            {scene.quote && (
              <>
                <dt className="text-muted-foreground">Цитата</dt>
                <dd className="italic text-muted-foreground">«{scene.quote}»</dd>
              </>
            )}

            {scene.probability !== null && (
              <>
                <dt className="text-muted-foreground">Вероятность</dt>
                <dd className="tabular-nums text-foreground">
                  {Math.round(scene.probability * 100)}%
                </dd>
              </>
            )}

            {scene.reason && (
              <>
                <dt className="text-muted-foreground">Основание</dt>
                <dd className="text-foreground">{scene.reason}</dd>
              </>
            )}

            {scene.recommendation && (
              <>
                <dt className="text-muted-foreground">Рекомендация</dt>
                <dd>
                  <span className="inline-flex items-center rounded-md bg-accent px-2 py-0.5 text-xs font-medium text-foreground">
                    {REC_LABELS[scene.recommendation] || scene.recommendation}
                  </span>
                </dd>
              </>
            )}
          </dl>
        </div>
      )}
    </div>
  );
}

export default function BooksPage() {
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [fileName, setFileName] = useState<string>("");
  const [fileSize, setFileSize] = useState<number>(0);
  const [bookId, setBookId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"violations" | "all">("violations");

  const processBook = async (file: File) => {
    setStatus("uploading");
    setFileName(file.name);
    setFileSize(file.size);
    setError(null);
    setAnalysis(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const uploadRes = await fetch(`${getApiBase()}/api/books/upload`, {
        method: "POST",
        body: formData,
      });

      if (!uploadRes.ok) {
        const errText = await uploadRes.text();
        throw new Error(`Ошибка загрузки: ${errText}`);
      }

      const uploaded = await uploadRes.json();
      setBookId(uploaded.id);
      setStatus("analyzing");

      const analyzeRes = await fetch(
        `${getApiBase()}/api/books/${uploaded.id}/analyze`,
        { method: "POST" }
      );

      if (!analyzeRes.ok) {
        const errText = await analyzeRes.text();
        throw new Error(`Ошибка анализа: ${errText}`);
      }

      const result = await analyzeRes.json();
      setAnalysis(result);
      setStatus("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Неизвестная ошибка");
      setStatus("error");
    }
  };

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles.length > 0 && status !== "uploading" && status !== "analyzing") {
        processBook(acceptedFiles[0]);
      }
    },
    [status]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    maxFiles: 1,
    maxSize: 500 * 1024 * 1024,
    disabled: status === "uploading" || status === "analyzing",
  });

  const reset = () => {
    setStatus("idle");
    setFileName("");
    setFileSize(0);
    setBookId(null);
    setAnalysis(null);
    setError(null);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
  };

  const riskyScenes = analysis?.scenes.filter((s) => s.risk) || [];
  const displayScenes =
    tab === "violations" ? riskyScenes : analysis?.scenes || [];
  const summary = analysis?.summary;

  const isProcessing = status === "uploading" || status === "analyzing";

  return (
    <AppLayout
      breadcrumb={[{ label: "Главная", href: "/" }, { label: "Книги" }]}
    >
      <div className="mx-auto max-w-6xl space-y-7">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Анализ книг
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Загрузите PDF-файл книги для проверки на соответствие требованиям
            </p>
          </div>
          {status !== "idle" && (
            <Button variant="outline" size="lg" onClick={reset} disabled={isProcessing}>
              Загрузить другую
            </Button>
          )}
        </div>

        {status === "idle" && (
          <div
            {...getRootProps()}
            className={cn(
              "cursor-pointer rounded-2xl border border-dashed p-12 text-center transition-all",
              isDragActive
                ? "border-primary bg-primary/[0.06]"
                : "border-border bg-card hover:border-primary/40 hover:bg-accent"
            )}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-4">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                <Upload className="h-7 w-7 text-primary" />
              </div>
              {isDragActive ? (
                <p className="text-lg font-medium text-primary">
                  Отпустите файл для загрузки
                </p>
              ) : (
                <div>
                  <p className="text-lg font-medium text-foreground">
                    Перетащите PDF-файл книги или нажмите для выбора
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    PDF до 500 МБ, до 1000 страниц
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {isProcessing && (
          <div className="rounded-2xl border border-border bg-card p-8">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-foreground">{fileName}</p>
                <p className="text-xs text-muted-foreground">{formatSize(fileSize)}</p>
              </div>
            </div>
            <div className="mt-6 flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <div>
                <p className="text-sm font-medium text-foreground">
                  {status === "uploading"
                    ? "Загрузка файла…"
                    : "Анализ текста через Gemini…"}
                </p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {status === "uploading"
                    ? "Файл загружается на сервер"
                    : "Извлечение текста и проверка на соответствие требованиям. Это может занять несколько минут."}
                </p>
              </div>
            </div>
          </div>
        )}

        {status === "error" && (
          <div className="rounded-2xl border border-critical-border bg-critical-soft p-8">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-6 w-6 text-critical" />
              <div>
                <p className="text-sm font-medium text-critical">
                  Ошибка при обработке
                </p>
                <p className="mt-0.5 text-xs text-critical/80">{error}</p>
              </div>
            </div>
          </div>
        )}

        {status === "done" && analysis && (
          <div className="flex flex-col gap-6 lg:flex-row">
            <aside className="w-full shrink-0 lg:w-80">
              <div className="sticky top-6 space-y-5">
                <div className="flex items-center gap-2.5">
                  <CheckCircle className="h-5 w-5 text-success" />
                  <h3 className="text-sm font-semibold text-foreground">
                    Анализ завершён
                  </h3>
                </div>

                <div className="space-y-3 border-t border-border pt-4 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Книга</span>
                    <span className="ml-2 max-w-[160px] truncate font-medium text-foreground">
                      {analysis.video_title || fileName}
                    </span>
                  </div>
                  {analysis.duration && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Объём</span>
                      <span className="font-medium text-foreground">
                        {analysis.duration}
                      </span>
                    </div>
                  )}
                </div>

                {summary && (
                  <>
                    <div className="border-t border-border pt-4">
                      <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                        Результаты проверки
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
                              Предупреждения
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
                        <p className="text-muted-foreground">Фрагментов</p>
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
                          {Object.entries(summary.risk_categories).map(
                            ([cat, count]) => (
                              <span
                                key={cat}
                                className="rounded-md bg-accent px-2 py-0.5 text-xs text-foreground"
                              >
                                {RISK_LABELS[cat] || cat} ({count})
                              </span>
                            )
                          )}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {bookId && (
                  <Button
                    className="w-full gap-2"
                    size="lg"
                    onClick={() => {
                      window.open(
                        `${getApiBase()}/api/books/${bookId}/report`,
                        "_blank"
                      );
                    }}
                  >
                    <Download className="h-4 w-4" />
                    Скачать отчёт
                  </Button>
                )}
              </div>
            </aside>

            <div className="min-w-0 flex-1">
              <div className="mb-4 flex items-center gap-5 border-b border-border">
                <button
                  onClick={() => setTab("violations")}
                  className={cn(
                    "-mb-px border-b-2 pb-2.5 text-sm font-medium transition-colors",
                    tab === "violations"
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  Нарушения ({riskyScenes.length})
                </button>
                <button
                  onClick={() => setTab("all")}
                  className={cn(
                    "-mb-px border-b-2 pb-2.5 text-sm font-medium transition-colors",
                    tab === "all"
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  Все фрагменты ({analysis.scenes.length})
                </button>
              </div>

              <div className="space-y-3">
                {displayScenes.map((scene) => (
                  <FragmentCard key={scene.id} scene={scene} />
                ))}
                {displayScenes.length === 0 && (
                  <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
                    {tab === "violations"
                      ? "Нарушений не обнаружено"
                      : "Фрагменты не найдены"}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
