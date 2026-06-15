"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, type ProjectAPI, type VideoFileAPI } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";

type WorkspaceContextValue = {
  projects: ProjectAPI[];
  recentFiles: VideoFileAPI[];
  inProgressCount: number;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);
const CACHE_KEY = "fc-workspace-v1";

function readCache(): {
  projects: ProjectAPI[];
  recent_files: VideoFileAPI[];
  in_progress_count: number;
} | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as {
      projects: ProjectAPI[];
      recent_files: VideoFileAPI[];
      in_progress_count: number;
    };
  } catch {
    return null;
  }
}

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [recentFiles, setRecentFiles] = useState<VideoFileAPI[]>([]);
  const [inProgressCount, setInProgressCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cached = readCache();
    if (!cached?.projects?.length) return;
    setProjects(cached.projects);
    setRecentFiles(cached.recent_files);
    setInProgressCount(cached.in_progress_count ?? 0);
    setLoading(false);
  }, []);

  const refresh = useCallback(async () => {
    if (!user) {
      setProjects([]);
      setRecentFiles([]);
      setInProgressCount(0);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const summary = await api.workspace.summary(24);
      setProjects(summary.projects);
      setRecentFiles(summary.recent_files);
      setInProgressCount(summary.in_progress_count);
      try {
        sessionStorage.setItem(CACHE_KEY, JSON.stringify(summary));
      } catch {
        /* ignore quota */
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить данные");
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (authLoading) return;
    void refresh();
  }, [authLoading, refresh]);

  useEffect(() => {
    if (!user) return;
    const poll = window.setInterval(() => {
      void refresh();
    }, 30_000);
    return () => window.clearInterval(poll);
  }, [user, refresh]);

  // Background driver: keep in-progress analyses moving app-wide. Long videos are
  // analyzed segment-by-segment, and each `GET /api/files/{id}` synchronously runs
  // one segment on the server. Polling here means analyses keep advancing on any
  // page and even after a full page reload (they resume from server state), not
  // just while the upload dialog is open. At most one in-flight drive per file.
  const recentRef = useRef<VideoFileAPI[]>([]);
  recentRef.current = recentFiles;
  const drivingRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!user) return;
    const WORKING = new Set(["uploading", "uploaded", "analyzing"]);
    const tick = () => {
      for (const file of recentRef.current) {
        if (!WORKING.has((file.status || "").toLowerCase())) continue;
        if (drivingRef.current.has(file.id)) continue;
        drivingRef.current.add(file.id);
        void api.files
          .get(file.id)
          .catch(() => {})
          .finally(() => {
            drivingRef.current.delete(file.id);
            void refresh();
          });
      }
    };
    const interval = window.setInterval(tick, 8_000);
    tick();
    return () => window.clearInterval(interval);
  }, [user, refresh]);

  const value = useMemo(
    () => ({
      projects,
      recentFiles,
      inProgressCount,
      loading: authLoading || (loading && projects.length === 0),
      error,
      refresh,
    }),
    [projects, recentFiles, inProgressCount, authLoading, loading, error, refresh]
  );

  return (
    <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
  );
}

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used within WorkspaceProvider");
  }
  return ctx;
}
