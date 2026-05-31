import {
  getDemoAnalysis,
  getDemoFile,
  getDemoProject,
  getDemoProjects,
  getDemoRecent,
} from "./demo-data";

export function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (
    typeof window !== "undefined" &&
    window.location.hostname !== "localhost" &&
    window.location.hostname !== "127.0.0.1"
  ) {
    return "";
  }
  return "http://localhost:8000";
}

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  if (DEMO_MODE) {
    return demoRequest<T>(path, options);
  }

  const res = await fetch(`${getApiBase()}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

function demoRequest<T>(path: string, options?: RequestInit): T {
  const method = options?.method?.toUpperCase() ?? "GET";

  if (method !== "GET") {
    throw new Error("В демо-режиме доступен только просмотр готовых примеров");
  }

  if (path === "/api/projects") {
    return getDemoProjects() as T;
  }

  const projectMatch = path.match(/^\/api\/projects\/([^/]+)$/);
  if (projectMatch) {
    const project = getDemoProject(projectMatch[1]);
    if (!project) throw new Error(`API error 404: project`);
    return project as T;
  }

  const recentMatch = path.match(/^\/api\/files\/recent\?limit=(\d+)$/);
  if (recentMatch) {
    return getDemoRecent(Number(recentMatch[1])) as T;
  }

  const fileMatch = path.match(/^\/api\/files\/([^/]+)$/);
  if (fileMatch && !path.endsWith("/analysis")) {
    const file = getDemoFile(fileMatch[1]);
    if (!file) throw new Error(`API error 404: file`);
    return file as T;
  }

  const analysisMatch = path.match(/^\/api\/files\/([^/]+)\/analysis$/);
  if (analysisMatch) {
    const analysis = getDemoAnalysis(analysisMatch[1]);
    if (!analysis) throw new Error(`API error 404: analysis`);
    return analysis as T;
  }

  if (path === "/api/health") {
    return { status: "ok", service: "framecheck-demo" } as T;
  }

  throw new Error(`API error 404: ${path}`);
}

export interface AnalysisSummaryAPI {
  total_scenes: number;
  risky_scenes: number;
  risk_categories: Record<string, number>;
  critical_count: number;
  warning_count: number;
  recommended_age_rating?: string | null;
  age_rating_reason?: string | null;
  age_rating_triggers?: AgeRatingTriggerAPI[];
  entities?: EntityAPI[];
  markings_detected?: MarkingAPI[];
}

export interface AgeRatingTriggerAPI {
  scene_number?: number;
  start_time?: string;
  end_time?: string;
  trigger?: string;
  reason?: string;
}

export interface EntityAPI {
  type?: string;
  name?: string;
  scene_number?: number;
  context?: string;
}

export interface MarkingAPI {
  type?: string;
  text?: string;
  scene_number?: number;
  start_time?: string;
}

export interface AnalysisBriefAPI {
  id: string;
  status: string;
  summary: AnalysisSummaryAPI | null;
  analyzed_at: string | null;
}

export interface ProjectAPI {
  id: string;
  name: string;
  created_at: string;
  files_count?: number;
  folders: FolderAPI[];
  files: VideoFileAPI[];
}

export interface FolderAPI {
  id: string;
  name: string;
  project_id: string;
  created_at: string;
}

export interface VideoFileAPI {
  id: string;
  name: string;
  size: number;
  status: string;
  progress: number;
  project_id: string;
  folder_id: string | null;
  storage_path: string | null;
  analysis_id: string | null;
  analysis?: AnalysisBriefAPI | null;
  created_at: string;
}

export interface SceneAPI {
  id: string;
  analysis_id: string;
  scene_number: number;
  start_time: string | null;
  end_time: string | null;
  description: string | null;
  risk: string | null;
  mode: string | null;
  risk_level: string | null;
  probability: number | null;
  reason: string | null;
  quote: string | null;
  text_in_frame: string | null;
  recommendation: string | null;
}

export interface AnalysisAPI {
  id: string;
  video_file_id: string;
  video_title: string | null;
  duration: string | null;
  analyzed_at: string | null;
  summary: AnalysisSummaryAPI | null;
  status: string;
  created_at: string;
  scenes: SceneAPI[];
}

export const api = {
  projects: {
    list: () => request<ProjectAPI[]>("/api/projects"),
    get: (id: string) => request<ProjectAPI>(`/api/projects/${id}`),
    create: (name: string) =>
      request<ProjectAPI>("/api/projects", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
  },

  files: {
    get: (id: string) => request<VideoFileAPI>(`/api/files/${id}`),
    recent: (limit = 12) =>
      request<VideoFileAPI[]>(`/api/files/recent?limit=${limit}`),
    getAnalysis: (id: string) =>
      request<AnalysisAPI>(`/api/files/${id}/analysis`),
    analyze: (id: string) => {
      if (DEMO_MODE) {
        return Promise.reject(new Error("Анализ недоступен в демо на GitHub Pages"));
      }
      return request<AnalysisAPI>(`/api/files/${id}/analyze`, { method: "POST" });
    },
    getReportUrl: (id: string) => `${getApiBase()}/api/files/${id}/report`,
    upload: async (
      projectId: string,
      file: File,
      folderId?: string,
      onProgress?: (progress: number) => void
    ): Promise<VideoFileAPI> => {
      if (DEMO_MODE) {
        throw new Error("Загрузка недоступна в демо на GitHub Pages");
      }

      const formData = new FormData();
      formData.append("file", file);

      const params = new URLSearchParams({ project_id: projectId });
      if (folderId) params.append("folder_id", folderId);

      const xhr = new XMLHttpRequest();

      return new Promise((resolve, reject) => {
        xhr.upload.addEventListener("progress", (e) => {
          if (e.lengthComputable && onProgress) {
            onProgress(Math.round((e.loaded / e.total) * 100));
          }
        });

        xhr.addEventListener("load", () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            reject(new Error(`Upload failed: ${xhr.status}`));
          }
        });

        xhr.addEventListener("error", () => reject(new Error("Upload failed")));

        xhr.open("POST", `${getApiBase()}/api/files/upload?${params.toString()}`);
        xhr.send(formData);
      });
    },
  },

  health: () => request<{ status: string }>("/api/health"),
};
