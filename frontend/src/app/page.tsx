"use client";

import { AppLayout } from "@/components/layout/app-layout";
import { Search, Folder, LayoutGrid, List, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { cn } from "@/lib/utils";
import { ReportsList } from "@/components/reports/reports-list";
import { Skeleton } from "@/components/ui/skeleton";
import { useWorkspace } from "@/contexts/workspace-context";
import { api, type ProjectAPI, type VideoFileAPI } from "@/lib/api";

const SEARCH_DEBOUNCE_MS = 180;

export default function HomePage() {
  const { projects, recentFiles, loading, error } = useWorkspace();
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [activeTab, setActiveTab] = useState<"projects" | "reports">("projects");
  const [query, setQuery] = useState("");
  const [searchProjects, setSearchProjects] = useState<ProjectAPI[]>([]);
  const [searchFiles, setSearchFiles] = useState<VideoFileAPI[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);

  const recent = recentFiles;
  const trimmedQuery = query.trim();
  const isSearching = trimmedQuery.length > 0;

  useEffect(() => {
    if (!trimmedQuery) {
      setSearchProjects([]);
      setSearchFiles([]);
      setSearchLoading(false);
      return;
    }

    setSearchLoading(true);
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const res = await api.search(trimmedQuery, 25);
        if (controller.signal.aborted) return;
        setSearchProjects(res.projects ?? []);
        setSearchFiles(res.files ?? []);
      } catch {
        if (!controller.signal.aborted) {
          setSearchProjects([]);
          setSearchFiles([]);
        }
      } finally {
        if (!controller.signal.aborted) setSearchLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [trimmedQuery]);

  const displayProjects = useMemo(
    () => (isSearching ? searchProjects : projects),
    [isSearching, searchProjects, projects]
  );

  const analyzedRecent = useMemo(
    () => recent.filter((f) => (f.status || "").toLowerCase() === "analyzed"),
    [recent]
  );

  const displayReports = useMemo(
    () =>
      isSearching
        ? searchFiles.filter((f) => (f.status || "").toLowerCase() === "analyzed")
        : analyzedRecent,
    [isSearching, searchFiles, analyzedRecent]
  );

  const displayRecent = useMemo(
    () => (isSearching ? searchFiles : recent),
    [isSearching, searchFiles, recent]
  );

  const showEmptySearch =
    isSearching &&
    !searchLoading &&
    (activeTab === "reports"
      ? displayReports.length === 0
      : displayProjects.length === 0 && displayRecent.length === 0);

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

        <div className="relative w-full">
          {searchLoading ? (
            <Loader2 className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
          ) : (
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          )}
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Поиск по проектам и отчётам"
            className="h-14 rounded-xl pl-11 text-sm"
            disabled={loading && !query}
          />
        </div>

        {error && (
          <p className="text-sm text-destructive">
            {error}. Обновите страницу или проверьте соединение с API.
          </p>
        )}

        <div className="flex items-center gap-4 border-b border-border pb-2">
          <button
            type="button"
            onClick={() => setActiveTab("projects")}
            className={cn(
              "text-sm font-medium transition-colors",
              activeTab === "projects"
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Проекты
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("reports")}
            className={cn(
              "text-sm font-medium transition-colors",
              activeTab === "reports"
                ? "text-foreground"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            Отчёты
          </button>
          {activeTab === "projects" && (
            <div className="ml-auto flex gap-1">
              <button
                type="button"
                onClick={() => setViewMode("grid")}
                className={cn(
                  "rounded-md p-1.5",
                  viewMode === "grid" ? "bg-muted text-foreground" : "text-muted-foreground"
                )}
                aria-label="Сетка"
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => setViewMode("list")}
                className={cn(
                  "rounded-md p-1.5",
                  viewMode === "list" ? "bg-muted text-foreground" : "text-muted-foreground"
                )}
                aria-label="Список"
              >
                <List className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>

        {showEmptySearch ? (
          <div className="rounded-xl border border-dashed border-border px-6 py-12 text-center">
            <p className="text-sm text-muted-foreground">
              Ничего не найдено по «{trimmedQuery}»
            </p>
          </div>
        ) : loading && projects.length === 0 && !isSearching ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-28 rounded-xl" />
            ))}
          </div>
        ) : activeTab === "reports" ? (
          <ReportsList
            files={displayReports}
            emptyMessage={
              isSearching
                ? `Нет отчётов по запросу «${trimmedQuery}»`
                : "Пока нет готовых отчётов"
            }
          />
        ) : displayProjects.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border px-6 py-12 text-center">
            <p className="text-sm text-muted-foreground">
              {isSearching
                ? `Нет проектов по запросу «${trimmedQuery}»`
                : (
                  <>
                    Пока нет проектов.{" "}
                    <Link href="/projects" className="text-primary hover:underline">
                      Создать проект
                    </Link>
                  </>
                  )}
            </p>
          </div>
        ) : viewMode === "grid" ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {displayProjects.map((project) => (
              <Link
                key={project.id}
                href={`/project/${project.id}`}
                className="rounded-xl border border-border bg-card p-5 transition-colors hover:border-primary/30 hover:bg-muted/30"
              >
                <Folder className="mb-3 h-5 w-5 text-muted-foreground" />
                <h3 className="font-medium text-foreground">{project.name}</h3>
                <p className="mt-1 text-xs text-muted-foreground">
                  {project.files_count ?? 0} файлов
                </p>
              </Link>
            ))}
          </div>
        ) : (
          <ul className="divide-y divide-border rounded-xl border border-border">
            {displayProjects.map((project) => (
              <li key={project.id}>
                <Link
                  href={`/project/${project.id}`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-muted/40"
                >
                  <Folder className="h-4 w-4 text-muted-foreground" />
                  <span className="flex-1 font-medium">{project.name}</span>
                  <span className="text-xs text-muted-foreground">
                    {project.files_count ?? 0}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}

        {!loading && activeTab === "projects" && displayRecent.length > 0 && (
          <div>
            <h2 className="mb-3 text-sm font-medium text-muted-foreground">
              {isSearching ? "Найденные отчёты" : "Недавние файлы"}
            </h2>
            <ul className="space-y-1">
              {(isSearching ? displayRecent : displayRecent.slice(0, 6)).map((file) => (
                <li key={file.id}>
                  <Link
                    href={`/file/${file.id}`}
                    className="text-sm text-primary hover:underline"
                  >
                    {file.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
