import { getApiBase, type VideoFileAPI } from "@/lib/api";

const CHUNK_SIZE = 3 * 1024 * 1024;
const BLOB_MULTIPART_THRESHOLD = 4 * 1024 * 1024;
const UPLOAD_TIMEOUT_MS = 15 * 60 * 1000;

function isLocalDev(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

function shouldUseBlobUpload(): boolean {
  return false;
}

function shouldUseChunkUpload(file: File): boolean {
  // Локально — один POST на /upload (chunk API часто отсутствует на старом uvicorn).
  if (isLocalDev()) return false;
  return true;
}

async function uploadViaDirectPost(
  file: File,
  projectId: string,
  onProgress: (progress: number, hint?: string) => void
): Promise<VideoFileAPI> {
  onProgress(5, "Загрузка на сервер…");
  const formData = new FormData();
  formData.append("file", file);
  const uploadRes = await fetch(
    `${getApiBase()}/api/files/upload?project_id=${encodeURIComponent(projectId)}&auto_analyze=1`,
    { method: "POST", body: formData }
  );
  if (!uploadRes.ok) {
    const body = await uploadRes.text();
    throw new Error(`Upload failed: ${uploadRes.status} ${body}`);
  }
  onProgress(100, "Файл загружен");
  return uploadRes.json();
}

function readVideoDurationSeconds(file: File): Promise<number | undefined> {
  return new Promise((resolve) => {
    const url = URL.createObjectURL(file);
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      URL.revokeObjectURL(url);
      resolve(Number.isFinite(video.duration) ? video.duration : undefined);
    };
    video.onerror = () => {
      URL.revokeObjectURL(url);
      resolve(undefined);
    };
    video.src = url;
  });
}

export async function waitForAnalysis(
  fileId: string,
  onProgress: (progress: number) => void,
  options?: { alreadyStarted?: boolean }
): Promise<void> {
  if (!options?.alreadyStarted) {
    const analyzeRes = await fetch(`${getApiBase()}/api/files/${fileId}/analyze`, {
      method: "POST",
    });

    if (!analyzeRes.ok && analyzeRes.status !== 202) {
      const errBody = await analyzeRes.text();
      throw new Error(`Analysis failed: ${errBody}`);
    }
  }

  const deadline = Date.now() + 60 * 60 * 1000;
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, 5000));
    const statusRes = await fetch(`${getApiBase()}/api/files/${fileId}`);
    if (statusRes.status >= 500) {
      throw new Error("Ошибка сервера при проверке статуса анализа");
    }
    if (!statusRes.ok) continue;
    const fileState = await statusRes.json();
    if (fileState.status === "analyzed") return;
    if (fileState.status === "error") {
      throw new Error("Analysis failed on server");
    }
    onProgress(Math.min(98, fileState.progress ?? 70));
  }
  const finalRes = await fetch(`${getApiBase()}/api/files/${fileId}`);
  const finalFile = await finalRes.json();
  if (finalFile.status !== "analyzed") {
    throw new Error("Analysis timed out");
  }
}

function useBlobMultipart(file: File): boolean {
  return file.size >= BLOB_MULTIPART_THRESHOLD;
}

function blobPathname(file: File): string {
  const ext = file.name.includes(".") ? (file.name.split(".").pop() ?? "mp4") : "mp4";
  const safeExt = ext.replace(/[^a-zA-Z0-9]/g, "").toLowerCase() || "mp4";
  return `videos/${crypto.randomUUID()}.${safeExt}`;
}

async function uploadViaBlob(
  file: File,
  uploadUrl: string,
  onProgress: (progress: number, hint?: string) => void
): Promise<{ url: string }> {
  const { upload } = await import("@vercel/blob/client");
  const pathname = blobPathname(file);
  const useMultipart = useBlobMultipart(file);

  onProgress(5, useMultipart ? "Подготовка частей…" : "Подключение к хранилищу…");

  const startedAt = Date.now();
  let lastPercent = 0;
  const heartbeat = setInterval(() => {
    const sec = Math.round((Date.now() - startedAt) / 1000);
    if (lastPercent === 0 && sec >= 8) {
      onProgress(5, `Ожидание ответа от хранилища… ${sec} сек (проверьте интернет)`);
    }
  }, 3000);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);

  const runUpload = (multipart: boolean) =>
    upload(pathname, file, {
      access: "public",
      contentType: file.type || "video/mp4",
      handleUploadUrl: uploadUrl,
      multipart,
      abortSignal: controller.signal,
      onUploadProgress: ({ percentage }) => {
        lastPercent = percentage;
        onProgress(
          Math.max(5, Math.round(percentage * 0.85)),
          `Загрузка в облако… ${Math.round(percentage)}%`
        );
      },
    });

  try {
    if (!useMultipart) {
      return await runUpload(false);
    }
    try {
      return await runUpload(true);
    } catch {
      onProgress(3, "Повтор без multipart…");
      return await runUpload(false);
    }
  } catch (err) {
    if (controller.signal.aborted) {
      throw new Error("Загрузка заняла слишком много времени. Попробуйте снова.");
    }
    const message = err instanceof Error ? err.message : "Upload failed";
    if (/blob|token|storage/i.test(message)) {
      throw new Error(
        "Не удалось подключиться к Vercel Blob. Нужен BLOB_READ_WRITE_TOKEN в настройках Vercel."
      );
    }
    throw err instanceof Error ? err : new Error(message);
  } finally {
    clearInterval(heartbeat);
    clearTimeout(timeout);
  }
}

async function registerBlobAndAnalyze(
  file: File,
  projectId: string,
  blobUrl: string,
  onProgress: (progress: number, hint?: string) => void
): Promise<VideoFileAPI> {
  onProgress(90, "Регистрация и запуск анализа…");
  const res = await fetch(
    `${getApiBase()}/api/files/from-blob?project_id=${encodeURIComponent(projectId)}&auto_analyze=1`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        blob_url: blobUrl,
        filename: file.name,
        size: file.size,
      }),
    }
  );
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Register failed: ${res.status} ${body}`);
  }
  onProgress(100, "Файл загружен");
  return res.json();
}

async function uploadViaChunks(
  file: File,
  projectId: string,
  onProgress: (progress: number, hint?: string) => void
): Promise<VideoFileAPI> {
  const totalParts = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));

  onProgress(3, "Подготовка загрузки…");

  const durationSeconds = await readVideoDurationSeconds(file);

  const initRes = await fetch(`${getApiBase()}/api/files/upload-chunks/init`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      size: file.size,
      project_id: projectId,
      duration_seconds: durationSeconds,
    }),
  });
  if (!initRes.ok) {
    const body = await initRes.text();
    throw new Error(`Upload init failed: ${initRes.status} ${body}`);
  }

  const { session_id: sessionId } = (await initRes.json()) as {
    session_id: string;
    chunk_size: number;
    total_parts: number;
  };

  for (let part = 0; part < totalParts; part++) {
    const start = part * CHUNK_SIZE;
    const end = Math.min(start + CHUNK_SIZE, file.size);
    const chunk = file.slice(start, end);

    const chunkRes = await fetch(
      `${getApiBase()}/api/files/upload-chunks/${sessionId}/parts/${part}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/octet-stream" },
        body: chunk,
      }
    );
    if (!chunkRes.ok) {
      const body = await chunkRes.text();
      throw new Error(`Chunk ${part + 1}/${totalParts} failed: ${chunkRes.status} ${body}`);
    }

    const percent = Math.round(((part + 1) / totalParts) * 85);
    onProgress(percent, `Загрузка на сервер… ${part + 1}/${totalParts}`);
  }

  onProgress(90, "Сборка файла и запуск анализа…");
  const completeRes = await fetch(
    `${getApiBase()}/api/files/upload-chunks/${sessionId}/complete?auto_analyze=1`,
    { method: "POST" }
  );
  if (!completeRes.ok) {
    const body = await completeRes.text();
    throw new Error(`Upload complete failed: ${completeRes.status} ${body}`);
  }

  onProgress(100, "Файл загружен");
  return completeRes.json();
}

export async function uploadFileToProject(
  file: File,
  projectId: string,
  onProgress: (progress: number, hint?: string) => void
): Promise<VideoFileAPI> {
  if (shouldUseBlobUpload()) {
    const uploadUrl =
      typeof window !== "undefined"
        ? `${window.location.origin}/upload/blob`
        : "/upload/blob";

    let blob: { url: string };
    try {
      blob = await uploadViaBlob(file, uploadUrl, onProgress);
    } catch {
      onProgress(3, "Повторная попытка загрузки…");
      blob = await uploadViaBlob(file, uploadUrl, onProgress);
    }

    return registerBlobAndAnalyze(file, projectId, blob.url, onProgress);
  }

  if (shouldUseChunkUpload(file)) {
    try {
      return await uploadViaChunks(file, projectId, onProgress);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (/404/.test(message) && /upload-chunks/i.test(message)) {
        onProgress(3, "Chunk API недоступен, прямая загрузка…");
        return uploadViaDirectPost(file, projectId, onProgress);
      }
      throw err;
    }
  }

  return uploadViaDirectPost(file, projectId, onProgress);
}

export async function createUploadProject(): Promise<string> {
  const res = await fetch(`${getApiBase()}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: `Проект ${new Date().toLocaleDateString("ru-RU")}` }),
  });
  if (!res.ok) {
    throw new Error("Не удалось создать проект");
  }
  const project = await res.json();
  return project.id as string;
}
