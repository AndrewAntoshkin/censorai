"use client";

import { useCallback, useState } from "react";
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
import { cn } from "@/lib/utils";
import { getApiBase, type VideoFileAPI } from "@/lib/api";

interface UploadFile {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "uploaded" | "analyzing" | "done" | "error";
  statusHint?: string;
  error?: string;
  fileId?: string;
}

interface UploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const DIRECT_UPLOAD_LIMIT = 4 * 1024 * 1024;

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} КБ`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} ГБ`;
}

function displayFileName(name: string): string {
  try {
    return decodeURIComponent(name);
  } catch {
    return name;
  }
}

function shouldUseBlobUpload(file: File): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  const isLocal = host === "localhost" || host === "127.0.0.1";
  return !isLocal || file.size > DIRECT_UPLOAD_LIMIT;
}

const STATUS_LABELS: Record<string, string> = {
  pending: "Готов к загрузке",
  uploading: "Загрузка…",
  uploaded: "Загружено, запуск анализа…",
  analyzing: "Анализ через Gemini · обычно 1–3 мин",
  done: "Анализ завершён",
  error: "Ошибка",
};

async function waitForAnalysis(
  fileId: string,
  onProgress: (progress: number) => void
): Promise<void> {
  const analyzeRes = await fetch(`${getApiBase()}/api/files/${fileId}/analyze`, {
    method: "POST",
  });

  if (analyzeRes.status === 202) {
    const deadline = Date.now() + 30 * 60 * 1000;
    while (Date.now() < deadline) {
      await new Promise((r) => setTimeout(r, 5000));
      const statusRes = await fetch(`${getApiBase()}/api/files/${fileId}`);
      if (!statusRes.ok) continue;
      const fileState = await statusRes.json();
      if (fileState.status === "analyzed") return;
      if (fileState.status === "error") {
        throw new Error("Analysis failed on server");
      }
      onProgress(Math.min(95, fileState.progress ?? 70));
    }
    const finalRes = await fetch(`${getApiBase()}/api/files/${fileId}`);
    const finalFile = await finalRes.json();
    if (finalFile.status !== "analyzed") {
      throw new Error("Analysis timed out");
    }
    return;
  }

  if (!analyzeRes.ok) {
    const errBody = await analyzeRes.text();
    throw new Error(`Analysis failed: ${errBody}`);
  }
}

async function uploadFileToProject(
  file: File,
  projectId: string,
  onProgress: (progress: number, hint?: string) => void
): Promise<VideoFileAPI> {
  if (shouldUseBlobUpload(file)) {
    const { upload } = await import("@vercel/blob/client");
    const uploadUrl =
      typeof window !== "undefined"
        ? `${window.location.origin}/upload/blob`
        : "/upload/blob";

    onProgress(8, "Подключение к хранилищу…");

    const startedAt = Date.now();
    const heartbeat = setInterval(() => {
      const sec = Math.round((Date.now() - startedAt) / 1000);
      if (sec >= 4) {
        onProgress(
          Math.min(84, 8 + sec),
          `Загрузка ${formatFileSize(file.size)} в облако… ${sec} сек`
        );
      }
    }, 2000);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15 * 60 * 1000);

    let blob: { url: string };
    try {
      blob = await upload(file.name, file, {
        access: "public",
        contentType: file.type || "video/mp4",
        handleUploadUrl: uploadUrl,
        // Multipart adds extra round-trips; keep simple upload up to 100 MB.
        multipart: file.size > 100 * 1024 * 1024,
        abortSignal: controller.signal,
        onUploadProgress: ({ percentage }) =>
          onProgress(
            Math.max(8, Math.round(percentage * 0.85)),
            `Загрузка в облако… ${Math.round(percentage)}%`
          ),
      });
    } catch (err) {
      if (controller.signal.aborted) {
        throw new Error(
          "Загрузка заняла слишком много времени. Проверьте интернет и попробуйте снова."
        );
      }
      const message = err instanceof Error ? err.message : "Upload failed";
      if (/blob|token|storage/i.test(message)) {
        throw new Error(
          "Не удалось подключиться к Vercel Blob. В настройках проекта нужен BLOB_READ_WRITE_TOKEN."
        );
      }
      throw err instanceof Error ? err : new Error(message);
    } finally {
      clearInterval(heartbeat);
      clearTimeout(timeout);
    }

    onProgress(90, "Регистрация файла…");
    const res = await fetch(
      `${getApiBase()}/api/files/from-blob?project_id=${encodeURIComponent(projectId)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          blob_url: blob.url,
          filename: file.name,
          size: file.size,
        }),
      }
    );
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Upload failed: ${res.status} ${body}`);
    }
    onProgress(100, "Файл загружен");
    return res.json();
  }

  const formData = new FormData();
  formData.append("file", file);
  const uploadRes = await fetch(
    `${getApiBase()}/api/files/upload?project_id=${encodeURIComponent(projectId)}`,
    { method: "POST", body: formData }
  );
  if (!uploadRes.ok) throw new Error(`Upload failed: ${uploadRes.status}`);
  onProgress(50);
  return uploadRes.json();
}

export function UploadModal({ open, onOpenChange }: UploadModalProps) {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const router = useRouter();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map((file) => ({
      file,
      progress: 0,
      status: "pending" as const,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "video/*": [".mp4", ".avi", ".mkv", ".mov", ".wmv"],
    },
    maxSize: 500 * 1024 * 1024,
  });

  const updateFile = (index: number, updates: Partial<UploadFile>) => {
    setFiles((prev) => prev.map((f, i) => (i === index ? { ...f, ...updates } : f)));
  };

  const uploadAndAnalyze = async () => {
    setIsProcessing(true);

    let projectId: string;
    try {
      const res = await fetch(`${getApiBase()}/api/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: `Проект ${new Date().toLocaleDateString("ru-RU")}` }),
      });
      const project = await res.json();
      projectId = project.id;
    } catch {
      setIsProcessing(false);
      return;
    }

    for (let i = 0; i < files.length; i++) {
      if (files[i].status !== "pending") continue;

      updateFile(i, { status: "uploading", progress: 5, statusHint: "Старт…" });

      try {
        const uploadedFile = await uploadFileToProject(
          files[i].file,
          projectId,
          (progress, hint) => updateFile(i, { progress, statusHint: hint })
        );
        updateFile(i, {
          status: "uploaded",
          progress: 100,
          fileId: uploadedFile.id,
          statusHint: "Запуск анализа…",
        });

        updateFile(i, { status: "analyzing", progress: 10, statusHint: "Отправка в Replicate…" });
        const idx = i;
        const creep = setInterval(() => {
          setFiles((prev) =>
            prev.map((f, j) =>
              j === idx && f.status === "analyzing" && f.progress < 95
                ? { ...f, progress: f.progress + 1 }
                : f
            )
          );
        }, 1500);

        try {
          await waitForAnalysis(uploadedFile.id, (progress) =>
            updateFile(i, {
              status: "analyzing",
              progress,
              statusHint: "Анализ видео · обычно 1–3 мин",
            })
          );
        } finally {
          clearInterval(creep);
        }

        updateFile(i, { status: "done", progress: 100 });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        updateFile(i, { status: "error", error: message });
      }
    }
    setIsProcessing(false);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleClose = (isOpen: boolean) => {
    if (isProcessing) return;
    if (!isOpen) {
      setFiles([]);
    }
    onOpenChange(isOpen);
  };

  const doneFile = files.find((f) => f.status === "done" && f.fileId);
  const canViewResult = !!doneFile;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Загрузка файлов</DialogTitle>
        </DialogHeader>

        <div
          {...getRootProps()}
          className={cn(
            "cursor-pointer rounded-xl border border-dashed p-8 text-center transition-colors",
            isDragActive
              ? "border-primary bg-primary/[0.06]"
              : "border-border hover:border-primary/40 hover:bg-accent",
            isProcessing && "pointer-events-none opacity-50"
          )}
        >
          <input {...getInputProps()} disabled={isProcessing} />
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
                  MP4, AVI, MKV, MOV, WMV до 500 МБ
                </p>
              </>
            )}
          </div>
        </div>

        {files.length > 0 && (
          <div className="mt-4 space-y-3 max-h-60 overflow-y-auto">
            {files.map((uploadFile, index) => (
              <div
                key={index}
                className="flex items-center gap-3 rounded-lg border border-border bg-card p-3"
              >
                <FileVideo className="h-5 w-5 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <div className="mb-1 flex items-center justify-between">
                    <p className="truncate text-sm font-medium text-foreground">
                      {displayFileName(uploadFile.file.name)}
                    </p>
                    <span className="ml-2 shrink-0 text-xs text-muted-foreground">
                      {formatFileSize(uploadFile.file.size)}
                    </span>
                  </div>
                  {(uploadFile.status === "uploading" || uploadFile.status === "analyzing") && (
                    <div className="space-y-1">
                      <Progress value={uploadFile.progress} className="h-1.5" />
                      <div className="flex items-center gap-1.5 text-xs text-primary">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        {uploadFile.statusHint || STATUS_LABELS[uploadFile.status]}
                      </div>
                    </div>
                  )}
                  {uploadFile.status === "uploaded" && (
                    <div className="flex items-center gap-1.5 text-xs text-primary">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      {STATUS_LABELS[uploadFile.status]}
                    </div>
                  )}
                  {uploadFile.status === "done" && (
                    <div className="flex items-center gap-1 text-xs text-success">
                      <CheckCircle className="h-3 w-3" />
                      {STATUS_LABELS[uploadFile.status]}
                    </div>
                  )}
                  {uploadFile.status === "error" && (
                    <div className="flex items-center gap-1 text-xs text-critical">
                      <AlertCircle className="h-3 w-3" />
                      {uploadFile.error || STATUS_LABELS[uploadFile.status]}
                    </div>
                  )}
                </div>
                {uploadFile.status === "pending" && !isProcessing && (
                  <button
                    onClick={() => removeFile(index)}
                    className="text-muted-foreground transition-colors hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="flex justify-end gap-2 mt-4">
          {canViewResult && (
            <Button
              onClick={() => {
                if (doneFile?.fileId) {
                  router.push(`/file/${doneFile.fileId}`);
                  handleClose(false);
                }
              }}
            >
              Посмотреть результат
            </Button>
          )}
          {files.length > 0 && files.some((f) => f.status === "pending") && (
            <Button
              onClick={uploadAndAnalyze}
              size="lg"
              disabled={isProcessing}
            >
              {isProcessing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Обработка...
                </>
              ) : (
                `Загрузить и анализировать (${files.filter((f) => f.status === "pending").length})`
              )}
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
