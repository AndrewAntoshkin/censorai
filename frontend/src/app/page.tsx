"use client";

import { AppLayout } from "@/components/layout/app-layout";
import { Search, Folder, LayoutGrid, List } from "lucide-react";
import { Input } from "@/components/ui/input";
import { api, getApiBase, type ProjectAPI, type VideoFileAPI } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { ReportsList } from "@/components/reports/reports-list";
import { Skeleton } from "@/components/ui/skeleton";

export default function HomePage() {
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [activeTab, setActiveTab] = useState<"projects" | "reports">("projects");
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [recent, setRecent] = useState<VideoFileAPI[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function loadHome() {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 120_000);

      try {
        let [p, r] = await Promise.all([
          fetch(`${getApiBase()}/api/projects`, { signal: controller.signal }).then((res) =>
            res.ok ? res.json() : []
          ),
          fetch(`${getApiBase()}/api/files/recent?limit=12`, { signal: controller.signal }).then(
            (res) => (res.ok ? res.json() : [])
          ),
        ]);

        if (p.length === 0 && r.length === 0) {
          await fetch(`${getApiBase()}/api/seed-demo`, {
            method: "POST",
            signal: controller.signal,
          }).catch(() => null);
          [p, r] = await Promise.all([
            fetch(`${getApiBase()}/api/projects`, { signal: controller.signal }).then((res) =>
              res.ok ? res.json() : []
            ),
            fetch(`${getApiBase()}/api/files/recent?limit=12`, { signal: controller.signal }).then(
              (res) => (res.ok ? res.json() : [])
            ),
          ]);
        }

        if (!active) return;
        setProjects(p);
        setRecent(r);
      } catch {
        // keep empty state
      } finally {
        clearTimeout(timeout);
        if (active) setLoading(false);
      }
    }

    void loadHome();
    return () => {
      active = false;
    };
  }, []);

  return (
    <AppLayout breadcrumb={[{ label: "Главная" }]}>
      <div className="mx-auto max-w-5xl space-y-10">
        <div>
          <h1 className="mb-1 text-2xl font-semibold tracking-tight text-foreground">
            Главная
          </h1>
          <p className="text-sm text-muted-foreground">
            Анализ видеоконтента на соответствие требованиям
          </p>
        </div>

        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Поиск по файлам и проектам"
            className="h-11 rounded-xl pl-10 text-sm"
          />
        </div>

        {loading ? (
          <div>
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-1 rounded-lg bg-muted p-0.5">
                <Skeleton className="h-8 w-20" />
                <Skeleton className="h-8 w-20" />
              </div>
              <div className="flex items-center gap-1 rounded-lg bg-muted p-0.5">
                <Skeleton className="h-8 w-8" />
                <Skeleton className="h-8 w-8" />
              </div>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-border bg-card p-4">
                  <Skeleton className="h-10 w-full" />
                </div>
              ))}
            </div>
          </div>
        ) : (
          <section>
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-1 rounded-lg bg-muted p-0.5">
                  <button
                    onClick={() => setActiveTab("projects")}
                    className={cn(
                      "rounded-md px-3 py-1 text-sm font-medium transition-colors",
                      activeTab === "projects"
                        ? "bg-card text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    Проекты
                  </button>
                  <button
                    onClick={() => setActiveTab("reports")}
                    className={cn(
                      "rounded-md px-3 py-1 text-sm font-medium transition-colors",
                      activeTab === "reports"
                        ? "bg-card text-foreground shadow-sm"
                        : "text-muted-foreground hover:text-foreground"
                    )}
                  >
                    Отчёты
                  </button>
                </div>

                {activeTab === "projects" && (
                  <div className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
                    <button
                      onClick={() => setViewMode("grid")}
                      className={cn(
                        "rounded-md p-1.5 transition-colors",
                        viewMode === "grid"
                          ? "bg-card text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground"
                      )}
                    >
                      <LayoutGrid className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setViewMode("list")}
                      className={cn(
                        "rounded-md p-1.5 transition-colors",
                        viewMode === "list"
                          ? "bg-card text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground"
                      )}
                    >
                      <List className="h-4 w-4" />
                    </button>
                  </div>
                )}
              </div>

              {activeTab === "projects" && viewMode === "grid" && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {projects.length === 0 && (
                    <div className="col-span-full rounded-xl border border-dashed border-border py-12 text-center text-sm text-muted-foreground">
                      Пока нет проектов. Загрузите видео или обновите страницу — демо-примеры
                      подгружаются при первом запуске сервера.
                    </div>
                  )}
                  {projects.map((project) => (
                    <Link
                      key={project.id}
                      href={`/project/${project.id}`}
                      className="group flex items-center gap-3 rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/30 hover:shadow-sm"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                        <Folder className="h-4.5 w-4.5 text-primary" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-foreground group-hover:text-primary">
                          {project.name}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {project.files_count ?? 0} файлов
                        </span>
                      </span>
                    </Link>
                  ))}
                </div>
              )}

              {activeTab === "projects" && viewMode === "list" && (
                <div className="overflow-hidden rounded-xl border border-border bg-card">
                  {projects.map((project, i) => (
                    <Link
                      key={project.id}
                      href={`/project/${project.id}`}
                      className={cn(
                        "flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent",
                        i > 0 && "border-t border-border"
                      )}
                    >
                      <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="text-sm font-medium text-foreground">
                        {project.name}
                      </span>
                      <span className="ml-auto text-xs text-muted-foreground">
                        {project.files_count ?? 0} файлов
                      </span>
                    </Link>
                  ))}
                </div>
              )}

              {activeTab === "reports" && (
                <ReportsList
                  files={recent}
                  onProjectAssigned={(fileId, projectId) =>
                    setRecent((prev) =>
                      prev.map((f) =>
                        f.id === fileId ? { ...f, project_id: projectId } : f
                      )
                    )
                  }
                />
              )}
          </section>
        )}
      </div>
    </AppLayout>
  );
}
