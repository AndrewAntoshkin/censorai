import { uploadFileToProject, waitForAnalysis } from "@/lib/upload-api";

export const MAX_CONCURRENT_UPLOADS = 3;

export type UploadJobStatus =
  | "pending"
  | "uploading"
  | "uploaded"
  | "analyzing"
  | "done"
  | "error";

export interface UploadJob {
  id: string;
  file: File;
  progress: number;
  status: UploadJobStatus;
  statusHint?: string;
  error?: string;
  fileId?: string;
  projectId?: string;
}

type Listener = () => void;

let jobs: UploadJob[] = [];
const listeners = new Set<Listener>();
let runningCount = 0;
const creepTimers = new Map<string, ReturnType<typeof setInterval>>();

function notify() {
  for (const listener of listeners) {
    listener();
  }
}

function patchJob(jobId: string, patch: Partial<UploadJob>) {
  jobs = jobs.map((j) => (j.id === jobId ? { ...j, ...patch } : j));
  notify();
}

export function subscribeUploadJobs(listener: Listener): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getUploadJobsSnapshot(): UploadJob[] {
  return jobs;
}

export function countActiveUploadJobs(): number {
  return jobs.filter((j) =>
    j.status === "uploading" || j.status === "uploaded" || j.status === "analyzing"
  ).length;
}

export function hasBackgroundUploadJobs(): boolean {
  return jobs.some(
    (j) =>
      j.status === "uploading" ||
      j.status === "uploaded" ||
      j.status === "analyzing" ||
      j.status === "pending"
  );
}

export function addPendingUploadJobs(files: File[]): void {
  const newJobs: UploadJob[] = files.map((file) => ({
    id: crypto.randomUUID(),
    file,
    progress: 0,
    status: "pending",
  }));
  jobs = [...jobs, ...newJobs];
  notify();
}

export function removePendingUploadJob(jobId: string): void {
  const job = jobs.find((j) => j.id === jobId);
  if (!job || job.status !== "pending") return;
  jobs = jobs.filter((j) => j.id !== jobId);
  notify();
}

export function clearFinishedUploadJobs(): void {
  jobs = jobs.filter((j) => j.status !== "done" && j.status !== "error");
  notify();
}

function startAnalysisCreep(jobId: string) {
  stopAnalysisCreep(jobId);
  const timer = setInterval(() => {
    jobs = jobs.map((j) =>
      j.id === jobId && j.status === "analyzing" && j.progress < 98
        ? { ...j, progress: j.progress + 1 }
        : j
    );
    notify();
  }, 1500);
  creepTimers.set(jobId, timer);
}

function stopAnalysisCreep(jobId: string) {
  const timer = creepTimers.get(jobId);
  if (timer) {
    clearInterval(timer);
    creepTimers.delete(jobId);
  }
}

function pumpQueue() {
  while (runningCount < MAX_CONCURRENT_UPLOADS) {
    const next = jobs.find((j) => j.status === "pending");
    if (!next) break;
    runningCount += 1;
    void runJob(next.id).finally(() => {
      runningCount -= 1;
      pumpQueue();
    });
  }
}

async function runJob(jobId: string) {
  const job = jobs.find((j) => j.id === jobId);
  if (!job || job.status !== "pending") return;

  patchJob(jobId, { status: "uploading", progress: 5, statusHint: "Старт…" });

  try {
    const uploadedFile = await uploadFileToProject(
      job.file,
      job.projectId,
      (progress, hint) => patchJob(jobId, { progress, statusHint: hint })
    );

    if (uploadedFile.status === "analyzed") {
      patchJob(jobId, {
        status: "done",
        progress: 100,
        fileId: uploadedFile.id,
        statusHint: "Анализ завершён",
      });
      return;
    }

    patchJob(jobId, {
      status: uploadedFile.status === "analyzing" ? "analyzing" : "uploaded",
      progress: uploadedFile.status === "analyzing" ? 30 : 100,
      fileId: uploadedFile.id,
      statusHint:
        uploadedFile.status === "analyzing"
          ? "Анализ запущен…"
          : "Запуск анализа…",
    });

    if (uploadedFile.status !== "analyzing") {
      patchJob(jobId, {
        status: "analyzing",
        progress: 10,
        statusHint: "Отправка в Replicate…",
      });
    }

    startAnalysisCreep(jobId);

    try {
      await waitForAnalysis(
        uploadedFile.id,
        (progress) =>
          patchJob(jobId, {
            status: "analyzing",
            progress,
            statusHint: "Анализ видео · 5–20 мин для длинных роликов",
          }),
        { alreadyStarted: uploadedFile.status === "analyzing" }
      );
    } finally {
      stopAnalysisCreep(jobId);
    }

    patchJob(jobId, { status: "done", progress: 100, statusHint: "Анализ завершён" });
  } catch (err) {
    stopAnalysisCreep(jobId);
    const message = err instanceof Error ? err.message : "Unknown error";
    patchJob(jobId, { status: "error", error: message });
  }
}

/** Start pending jobs (optional shared project for the whole batch). */
export function startUploadBatch(
  jobIds: string[],
  projectId?: string | null
): void {
  const pending = jobs.filter(
    (j) => jobIds.includes(j.id) && j.status === "pending"
  );
  if (pending.length === 0) return;

  if (projectId) {
    for (const job of pending) {
      patchJob(job.id, { projectId });
    }
  }

  pumpQueue();
}
