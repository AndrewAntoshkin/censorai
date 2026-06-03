"use client";

import { useCallback, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { useDropzone } from "react-dropzone";
import { Upload, X, FileVideo, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn, displayFileName } from "@/lib/utils";
import {
  MAX_CONCURRENT_UPLOADS,
  addPendingUploadJobs,
  clearFinishedUploadJobs,
  countActiveUploadJobs,
  getUploadJobsSnapshot,
  removePendingUploadJob,
  startUploadBatch,
  subscribeUploadJobs,
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
  uploaded: "Загружено, запуск анализа…",
  analyzing: "Анализ через Gemini · 5–20 мин для длинных видео",
  done: "Анализ завершён",
  error: "Ошибка",
};

export function UploadModal({ open, onOpenChange }: UploadModalProps) {
  const router = useRouter();

  const jobs = useSyncExternalStore(
    subscribeUploadJobs,
    getUploadJobsSnapshot,
    getUploadJobsSnapshot
  );

  const onDrop = useCallback((acceptedFiles: File[]) => {
    addPendingUploadJobs(acceptedFiles);
  }, []);

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

  const uploadAndAnalyze = () => {
    const ids = pendingJobs.map((j) => j.id);
    startUploadBatch(ids);
  };

  const handleClose = (isOpen: boolean) => {
    onOpenChange(isOpen);
  };

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
                {typeof window !== "undefined" &&
                  (window.location.hostname === "localhost" ||
                    window.location.hostname === "127.0.0.1") && (
                    <p className="text-xs text-muted-foreground">
                      Локально &gt;4 МБ: BLOB_READ_WRITE_TOKEN в backend/.env.secrets
                    </p>
                  )}
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
            <Button onClick={uploadAndAnalyze} size="lg">
              {hasActive ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  В очереди ({pendingJobs.length})
                </>
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

function JobRow({
  uploadJob,
  onRemove,
}: {
  uploadJob: UploadJob;
  onRemove: () => void;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-card p-3">
      <FileVideo className="h-5 w-5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center justify-between">
          <p className="truncate text-sm font-medium text-foreground">
            {displayFileName(uploadJob.file.name)}
          </p>
          <span className="ml-2 shrink-0 text-xs text-muted-foreground">
            {formatFileSize(uploadJob.file.size)}
          </span>
        </div>
        {(uploadJob.status === "uploading" || uploadJob.status === "analyzing") && (
          <div className="space-y-1">
            <Progress value={uploadJob.progress} className="h-1.5" />
            <div className="flex items-center gap-1.5 text-xs text-primary">
              <Loader2 className="h-3 w-3 animate-spin" />
              {uploadJob.statusHint || STATUS_LABELS[uploadJob.status]}
            </div>
          </div>
        )}
        {uploadJob.status === "uploaded" && (
          <div className="flex items-center gap-1.5 text-xs text-primary">
            <Loader2 className="h-3 w-3 animate-spin" />
            {STATUS_LABELS[uploadJob.status]}
          </div>
        )}
        {uploadJob.status === "done" && (
          <div className="flex items-center gap-1 text-xs text-success">
            <CheckCircle className="h-3 w-3" />
            {STATUS_LABELS[uploadJob.status]}
          </div>
        )}
        {uploadJob.status === "error" && (
          <div className="flex items-center gap-1 text-xs text-critical">
            <AlertCircle className="h-3 w-3" />
            {uploadJob.error || STATUS_LABELS[uploadJob.status]}
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
