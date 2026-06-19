"use client";

import { useCallback, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { Upload, X, FileVideo, CheckCircle, AlertCircle, Loader2, Shield, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { cn, displayFileName } from "@/lib/utils";
import type { UploadReportKind } from "@/lib/upload-api";
import {
  MAX_CONCURRENT_UPLOADS,
  addPendingUploadJobs,
  clearFinishedUploadJobs,
  countActiveUploadJobs,
  getUploadJobsSnapshot,
  removePendingUploadJob,
  startUploadBatch,
  subscribeUploadJobs,
  updatePendingJobsUploadOptions,
  type UploadJob,
} from "@/lib/upload-jobs";

interface UploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} ГБ`;
}

const STATUS_LABELS: Record<string, string> = {
  pending: "Готов к загрузке",
  uploading: "Загрузка…",
  uploaded: "Загружено, запуск…",
  analyzing: "Анализ через Gemini · 5–20 мин для длинных видео",
  done: "Готово",
  error: "Ошибка",
};

export function UploadModal({ open, onOpenChange }: UploadModalProps) {
  const router = useRouter();
  const [uploadMode, setUploadMode] = useState<UploadReportKind>("moderation");
  const [placementQuery, setPlacementQuery] = useState("");

  const jobs = useSyncExternalStore(
    subscribeUploadJobs,
    getUploadJobsSnapshot,
    getUploadJobsSnapshot
  );

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      addPendingUploadJobs(acceptedFiles, {
        reportKind: uploadMode,
        placementQuery: uploadMode === "placement" ? placementQuery : undefined,
      });
    },
    [uploadMode, placementQuery]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "video/*": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
    },
    maxSize: 500 * 1024 * 1024,
  });

  const pendingJobs = jobs.filter((j) => j.status === "pending");
  const activeCount = countActiveUploadJobs();
  const hasActive = activeCount > 0;
  const doneJob = jobs.find((j) => j.status === "done" && j.fileId);
  const canViewResult = !!doneJob;
  const allTerminal =
    jobs.length > 0 && jobs.every((j) => j.status === "done" || j.status === "error");

  const placementValid = uploadMode !== "placement" || placementQuery.trim().length >= 2;

  const uploadAndAnalyze = () => {
    if (!placementValid) return;
    updatePendingJobsUploadOptions({
      reportKind: uploadMode,
      placementQuery: placementQuery.trim(),
    });
    const ids = pendingJobs.map((j) => j.id);
    startUploadBatch(ids);
  };

  const handleClose = (isOpen: boolean) => {
    if (!isOpen) {
      setPlacementQuery("");
      setUploadMode("moderation");
    }
    onOpenChange(isOpen);
  };

  const isPlacement = uploadMode === "placement";

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Загрузка файлов</DialogTitle>
          {hasActive && (
            <p className="text-xs text-muted-foreground">
              Можно закрыть окно — до {MAX_CONCURRENT_UPLOADS} файлов обрабатываются параллельно
              {activeCount > 0 ? ` (сейчас ${activeCount})` : ""}
            </p>
          )}
        </DialogHeader>

        <div className="grid grid-cols-2 gap-2">
          <ModeButton
            active={uploadMode === "moderation"}
            onClick={() => setUploadMode("moderation")}
            icon={<Shield className="h-4 w-4" />}
            title="Анализ"
            description="Модерация и риски"
          />
          <ModeButton
            active={uploadMode === "placement"}
            onClick={() => setUploadMode("placement")}
            icon={<Sparkles className="h-4 w-4" />}
            title="Продакт плейсмент"
            description="Слоты для рекламы"
          />
        </div>

        {isPlacement && (
          <div className="space-y-1.5">
            <label htmlFor="placement-query" className="text-sm font-medium text-foreground">
              Что размещаем в кадре
            </label>
            <Input
              id="placement-query"
              value={placementQuery}
              onChange={(e) => setPlacementQuery(e.target.value)}
              placeholder="Например: бутылка, смартфон, чашка"
              className="h-10"
            />
            <p className="text-xs text-muted-foreground">
              Найдём моменты, куда можно нативно вставить предмет в монтаже
            </p>
          </div>
        )}

        <div
          {...getRootProps()}
          className={cn(
            "cursor-pointer rounded-xl border border-dashed p-8 text-center transition-colors",
            isDragActive
              ? "border-primary bg-primary/[0.06]"
              : "border-border hover:border-primary/40 hover:bg-accent"
          )}
        >
          <input {...getInputProps()} />
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Upload className="h-5 w-5 text-primary" />
            </div>
            {isDragActive ? (
              <p className="text-sm font-medium text-primary">
                Отпустите файлы для загрузки
              </p>
            ) : (
              <>
                <p className="text-sm font-medium text-foreground">
                  Перетащите файлы или нажмите для выбора
                </p>
                <p className="text-xs text-muted-foreground">
                  MP4, AVI, MKV, MOV, WMV до 500 МБ · до {MAX_CONCURRENT_UPLOADS} одновременно
                </p>
              </>
            )}
          </div>
        </div>

        {jobs.length > 0 && (
          <div className="mt-4 max-h-60 space-y-3 overflow-y-auto">
            {jobs.map((uploadJob) => (
              <JobRow
                key={uploadJob.id}
                uploadJob={uploadJob}
                onRemove={() => removePendingUploadJob(uploadJob.id)}
              />
            ))}
          </div>
        )}

        <div className="mt-4 flex justify-end gap-2">
          {allTerminal && jobs.length > 0 && (
            <Button variant="outline" onClick={() => clearFinishedUploadJobs()}>
              Очистить список
            </Button>
          )}
          {canViewResult && (
            <Button
              onClick={() => {
                if (doneJob?.fileId) {
                  router.push(`/file/${doneJob.fileId}`);
                  handleClose(false);
                }
              }}
            >
              Посмотреть результат
            </Button>
          )}
          {pendingJobs.length > 0 && (
            <Button onClick={uploadAndAnalyze} size="lg" disabled={!placementValid}>
              {hasActive ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  В очереди ({pendingJobs.length})
                </>
              ) : isPlacement ? (
                `Найти слоты (${pendingJobs.length})`
              ) : (
                `Загрузить и анализировать (${pendingJobs.length})`
              )}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ModeButton({
  active,
  onClick,
  icon,
  title,
  description,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition-colors",
        active
          ? "border-primary bg-primary/10 ring-1 ring-primary/30"
          : "border-border hover:border-primary/30 hover:bg-accent"
      )}
    >
      <span className={cn("flex items-center gap-2 text-sm font-medium", active && "text-primary")}>
        {icon}
        {title}
      </span>
      <span className="text-xs text-muted-foreground">{description}</span>
    </button>
  );
}

function JobRow({
  uploadJob,
  onRemove,
}: {
  uploadJob: UploadJob;
  onRemove: () => void;
}) {
  const isPlacement = uploadJob.reportKind === "placement";
  const statusLabel =
    uploadJob.status === "analyzing" && isPlacement
      ? "Поиск слотов · 5–20 мин для длинных видео"
      : uploadJob.status === "done" && isPlacement
        ? "Отчёт готов"
        : STATUS_LABELS[uploadJob.status];

  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-3">
      <FileVideo className="h-5 w-5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center justify-between gap-2">
          <p className="truncate text-sm font-medium text-foreground">
            {displayFileName(uploadJob.file.name)}
          </p>
          <span className="ml-2 shrink-0 text-xs text-muted-foreground">
            {formatFileSize(uploadJob.file.size)}
          </span>
        </div>
        {isPlacement && uploadJob.placementQuery && (
          <p className="mb-1 truncate text-xs text-muted-foreground">
            Поиск: «{uploadJob.placementQuery}»
          </p>
        )}
        {(uploadJob.status === "uploading" || uploadJob.status === "analyzing") && (
          <div className="space-y-1">
            <Progress value={uploadJob.progress} className="h-1.5" />
            <div className="flex items-center gap-1.5 text-xs text-primary">
              <Loader2 className="h-3 w-3 animate-spin" />
              {uploadJob.statusHint || statusLabel}
            </div>
          </div>
        )}
        {uploadJob.status === "uploaded" && (
          <div className="flex items-center gap-1.5 text-xs text-primary">
            <Loader2 className="h-3 w-3 animate-spin" />
            {statusLabel}
          </div>
        )}
        {uploadJob.status === "done" && (
          <div className="flex items-center gap-1 text-xs text-success">
            <CheckCircle className="h-3 w-3" />
            {statusLabel}
          </div>
        )}
        {uploadJob.status === "error" && (
          <div className="flex items-center gap-1 text-xs text-critical">
            <AlertCircle className="h-3 w-3" />
            {uploadJob.error || statusLabel}
          </div>
        )}
      </div>
      {uploadJob.status === "pending" && (
        <button
          type="button"
          onClick={onRemove}
          className="text-muted-foreground transition-colors hover:text-foreground"
          aria-label="Убрать из списка"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
