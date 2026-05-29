"use client";

import { AppLayout } from "@/components/layout/app-layout";
import { Search, Folder, Film, LayoutGrid, List, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { api, type ProjectAPI, type VideoFileAPI } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { FileStatusBadge } from "@/components/shared/file-status-badge";

export default function HomePage() {
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [activeTab, setActiveTab] = useState<"projects" | "reports">("projects");
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [recent, setRecent] = useState<VideoFileAPI[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([api.projects.list(), api.files.recent(12)])
      .then(([p, r]) => {
        if (!active) return;
        setProjects(p);
        setRecent(r);
      })
      .catch(() => {})
      .finally(() => active && setLoading(false));
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
          <div className="flex h-40 items-center justify-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Загрузка…
          </div>
        ) : (
          <>
            {recent.length > 0 && (
              <section>
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-foreground">Недавние</h2>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {recent.slice(0, 4).map((file) => (
                    <Link
                      key={file.id}
                      href={`/file/${file.id}`}
                      className="group rounded-xl border border-border bg-card p-3 transition-all hover:border-primary/30 hover:shadow-sm"
                    >
                      <div className="mb-3 flex aspect-[4/3] w-full items-center justify-center rounded-lg bg-muted">
                        <Film className="h-7 w-7 text-muted-foreground/60" />
                      </div>
                      <p className="truncate text-sm font-medium text-foreground group-hover:text-primary">
                        {file.name}
                      </p>
                    </Link>
                  ))}
                </div>
              </section>
            )}

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
                <div className="overflow-hidden rounded-xl border border-border bg-card">
                  {recent.length === 0 && (
                    <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                      Пока нет готовых отчётов
                    </div>
                  )}
                  {recent.map((file, i) => (
                    <Link
                      key={file.id}
                      href={`/file/${file.id}`}
                      className={cn(
                        "flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent",
                        i > 0 && "border-t border-border"
                      )}
                    >
                      <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="truncate text-sm text-foreground">
                        {file.name}
                      </span>
                      <FileStatusBadge
                        status={file.status}
                        progress={file.progress}
                        riskyScenes={file.analysis?.summary?.risky_scenes ?? null}
                        className="ml-auto shrink-0"
                      />
                    </Link>
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </AppLayout>
  );
}
