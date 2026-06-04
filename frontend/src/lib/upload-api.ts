import { getApiBase, type VideoFileAPI } from "@/lib/api";

function apiFetch(input: string, init?: RequestInit) {
  return fetch(input, { ...init, credentials: "include" });
}

const CHUNK_SIZE = 3 * 1024 * 1024;
const BLOB_MULTIPART_THRESHOLD = 4 * 1024 * 1024;
const UPLOAD_TIMEOUT_MS = 15 * 60 * 1000;
/** Chunk-via-API needs Blob or disk; never Postgres for large files on Vercel. */
const MAX_CHUNK_FALLBACK_BYTES = 50 * 1024 * 1024;

function blobQuotaUserMessage(): string {
  return (
    "Хранилище Vercel Blob переполнено (лимит Hobby — 1 ГБ). " +
    "Очистите Storage → Blob в Vercel Dashboard или вызовите очистку с сервера. " +
    "Загрузка через базу данных для больших файлов недоступна."
  );
}

function formatChunkUploadError(status: number, body: string, part: number, total: number): string {
  const lower = body.toLowerCase();
  if (lower.includes("storage quota exceeded") || lower.includes("quota exceeded")) {
    return blobQuotaUserMessage();
  }
  if (lower.includes("diskfull") || lower.includes("project size limit")) {
    return (
      "База Neon переполнена (лимит ~512 МБ на проект). " +
      "Очистите Vercel Blob и не используйте загрузку через чанки для больших файлов."
    );
  }
  return `Chunk ${part + 1}/${total} failed: ${status} ${body}`;
}

function isLocalDev(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1";
}

function shouldUseBlobUpload(): boolean {
  return !isLocalDev();
}

function shouldUseChunkUpload(_file: File): boolean {
  if (isLocalDev()) return false;
  return true;
}

function isBlobQuotaError(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("quota") ||
    lower.includes("storage quota") ||
    lower.includes("suspended") ||
    lower.includes("store has been suspended")
  );
}

type UploadStrategy = "s3" | "blob" | "none";

let cachedStrategy: UploadStrategy | null = null;

async function fetchUploadStrategy(): Promise<UploadStrategy> {
  if (cachedStrategy) return cachedStrategy;
  try {
    const res = await apiFetch(`${getApiBase()}/api/files/upload-strategy`);
    if (!res.ok) return "blob";
    const data = (await res.json()) as { method?: string };
    const method = data.method === "s3" || data.method === "blob" ? data.method : "none";
    cachedStrategy = method;
    return method;
  } catch {
    return "blob";
  }
}

async function blobStorageWritable(): Promise<boolean> {
  try {
    const res = await apiFetch(`${getApiBase()}/api/files/blob-selftest`, {
      method: "POST",
    });
    if (!res.ok) return false;
    const data = (await res.json()) as { ok?: boolean };
    return Boolean(data.ok);
  } catch {
    return false;
  }
}

function uploadQuery(projectId?: string | null, extra?: Record<string, string>): string {
  const params = new URLSearchParams({ auto_analyze: "1", ...extra });
  if (projectId) params.set("project_id", projectId);
  return params.toString();
}

async function uploadViaDirectPost(
  file: File,
  projectId: string | undefined,
  onProgress: (progress: number, hint?: string) => void
): Promise<VideoFileAPI> {
  onProgress(5, "Загрузка на сервер…");
  const formData = new FormData();
  formData.append("file", file);
  const uploadRes = await apiFetch(
    `${getApiBase()}/api/files/upload?${uploadQuery(projectId)}`,
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
    const analyzeRes = await apiFetch(`${getApiBase()}/api/files/${fileId}/analyze`, {
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
    const statusRes = await apiFetch(`${getApiBase()}/api/files/${fileId}`);
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
  const finalRes = await apiFetch(`${getApiBase()}/api/files/${fileId}`);
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

  onProgress(
    5,
    useMultipart
      ? "Подготовка частей… (на 300+ МБ первые % могут идти долго)"
      : "Подключение к хранилищу…"
  );

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
    const lower = message.toLowerCase();
    if (isBlobQuotaError(message)) {
      throw new Error("BLOB_QUOTA_EXCEEDED");
    }
    if (lower.includes("client token has expired")) {
      throw new Error("Сессия загрузки истекла. Закройте окно и загрузите файл снова.");
    }
    if (lower.includes("failed to  retrieve the client token")) {
      throw new Error(
        "Сервер не выдал токен для загрузки. Проверьте BLOB_READ_WRITE_TOKEN на backend в Vercel."
      );
    }
    throw new Error(message);
  } finally {
    clearInterval(heartbeat);
    clearTimeout(timeout);
  }
}

async function registerStorageAndAnalyze(
  file: File,
  projectId: string | undefined,
  storagePath: string,
  onProgress: (progress: number, hint?: string) => void
): Promise<VideoFileAPI> {
  onProgress(88, "Проверка длительности…");
  const durationSeconds = await readVideoDurationSeconds(file);
  onProgress(90, "Регистрация и запуск анализа…");
  const body: Record<string, unknown> = {
    filename: file.name,
    size: file.size,
    ...(durationSeconds !== undefined ? { duration_seconds: durationSeconds } : {}),
  };
  if (storagePath.startsWith("s3://")) {
    body.storage_path = storagePath;
  } else {
    body.blob_url = storagePath;
  }
  const res = await apiFetch(
    `${getApiBase()}/api/files/from-blob?${uploadQuery(projectId)}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Register failed: ${res.status} ${text}`);
  }
  onProgress(100, "Файл загружен");
  return res.json();
}

function uploadViaS3Presigned(
  file: File,
  projectId: string | undefined,
  onProgress: (progress: number, hint?: string) => void
): Promise<string> {
  return new Promise((resolve, reject) => {
    (async () => {
      onProgress(5, "Подготовка загрузки в R2…");
      const presignRes = await apiFetch(`${getApiBase()}/api/files/presign-upload`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          size: file.size,
          ...(projectId ? { project_id: projectId } : {}),
          content_type: file.type || "video/mp4",
        }),
      });
      if (!presignRes.ok) {
        const body = await presignRes.text();
        reject(new Error(`Presign failed: ${presignRes.status} ${body}`));
        return;
      }
      const presign = (await presignRes.json()) as {
        upload_url: string;
        storage_path: string;
        method: string;
        headers: Record<string, string>;
      };

      const xhr = new XMLHttpRequest();
      xhr.open(presign.method || "PUT", presign.upload_url);
      const headers = presign.headers || {};
      for (const [key, value] of Object.entries(headers)) {
        xhr.setRequestHeader(key, value);
      }

      xhr.upload.onprogress = (ev) => {
        if (!ev.lengthComputable) return;
        const pct = Math.round((ev.loaded / ev.total) * 85);
        onProgress(Math.max(5, pct), `Загрузка в хранилище… ${Math.round((ev.loaded / ev.total) * 100)}%`);
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(presign.storage_path);
        } else {
          reject(new Error(`R2 upload failed: ${xhr.status} ${xhr.responseText}`));
        }
      };
      xhr.onerror = () => reject(new Error("Сбой сети при загрузке в R2"));
      xhr.onabort = () => reject(new Error("Загрузка отменена"));
      xhr.send(file);
    })().catch(reject);
  });
}

async function uploadViaChunks(
  file: File,
  projectId: string | undefined,
  onProgress: (progress: number, hint?: string) => void
): Promise<VideoFileAPI> {
  const totalParts = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));

  onProgress(3, "Подготовка загрузки…");

  const durationSeconds = await readVideoDurationSeconds(file);

  const initRes = await apiFetch(`${getApiBase()}/api/files/upload-chunks/init`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filename: file.name,
      size: file.size,
      ...(projectId ? { project_id: projectId } : {}),
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

    const chunkRes = await apiFetch(
      `${getApiBase()}/api/files/upload-chunks/${sessionId}/parts/${part}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/octet-stream" },
        body: chunk,
      }
    );
    if (!chunkRes.ok) {
      const body = await chunkRes.text();
      throw new Error(
        formatChunkUploadError(chunkRes.status, body, part, totalParts)
      );
    }

    const percent = Math.round(((part + 1) / totalParts) * 85);
    onProgress(percent, `Загрузка на сервер… ${part + 1}/${totalParts}`);
  }

  onProgress(90, "Сборка файла и запуск анализа…");
  const completeRes = await apiFetch(
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

function canFallbackToChunks(file: File): boolean {
  return file.size <= MAX_CHUNK_FALLBACK_BYTES;
}

export async function uploadFileToProject(
  file: File,
  projectId: string | undefined,
  onProgress: (progress: number, hint?: string) => void
): Promise<VideoFileAPI> {
  if (shouldUseBlobUpload()) {
    const strategy = await fetchUploadStrategy();

    if (strategy === "s3") {
      const storagePath = await uploadViaS3Presigned(file, projectId, onProgress);
      return registerStorageAndAnalyze(file, projectId, storagePath, onProgress);
    }

    if (strategy === "none") {
      throw new Error(
        "Нет хранилища для загрузки. Подключите Cloudflare R2 (переменные S3_*) " +
          "или освободите Vercel Blob."
      );
    }

    const blobWritable = await blobStorageWritable();
    if (!blobWritable) {
      if (!canFallbackToChunks(file)) {
        throw new Error(blobQuotaUserMessage());
      }
      onProgress(2, "Blob переполнен — пробуем малую загрузку через API…");
      return uploadViaChunks(file, projectId, onProgress);
    }

    const uploadUrl = `${getApiBase()}/api/files/blob-upload`;

    try {
      const blob = await uploadViaBlob(file, uploadUrl, onProgress);
      return registerStorageAndAnalyze(file, projectId, blob.url, onProgress);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (message === "BLOB_QUOTA_EXCEEDED" || isBlobQuotaError(message)) {
        if (!canFallbackToChunks(file)) {
          throw new Error(blobQuotaUserMessage());
        }
        onProgress(2, "Blob переполнен — пробуем загрузку через API…");
        return uploadViaChunks(file, projectId, onProgress);
      }
      onProgress(3, "Повторная попытка загрузки…");
      try {
        const blob = await uploadViaBlob(file, uploadUrl, onProgress);
        return registerStorageAndAnalyze(file, projectId, blob.url, onProgress);
      } catch (retryErr) {
        const retryMsg = retryErr instanceof Error ? retryErr.message : String(retryErr);
        if (retryMsg === "BLOB_QUOTA_EXCEEDED" || isBlobQuotaError(retryMsg)) {
          if (!canFallbackToChunks(file)) {
            throw new Error(blobQuotaUserMessage());
          }
          return uploadViaChunks(file, projectId, onProgress);
        }
        throw retryErr;
      }
    }
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

