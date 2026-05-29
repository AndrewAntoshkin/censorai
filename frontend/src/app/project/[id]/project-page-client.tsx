"use client";

import { useEffect, useState } from "react";
import { AppLayout } from "@/components/layout/app-layout";
import { ArrowLeft, Folder, LayoutGrid, List, Film, Loader2 } from "lucide-react";
import { api, type ProjectAPI } from "@/lib/api";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { FileStatusBadge } from "@/components/shared/file-status-badge";

export function ProjectPageClient({ id }: { id: string }) {
  const [project, setProject] = useState<ProjectAPI | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [fileView, setFileView] = useState<"grid" | "list">("list");

  useEffect(() => {
    let active = true;
    setLoading(true);
    api.projects
      .get(id)
      .then((p) => active && setProject(p))
      .catch(() => active && setNotFound(true))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [id]);

  if (loading) {
    return (
      <AppLayout breadcrumb={[{ label: "Главная", href: "/" }, { label: "Загрузка…" }]}>
        <div className="flex h-64 items-center justify-center gap-3 text-sm text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
          Загрузка…
        </div>
      </AppLayout>
    );
  }

  if (notFound || !project) {
    return (
      <AppLayout breadcrumb={[{ label: "Главная", href: "/" }, { label: "Проект не найден" }]}>
        <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">
          Проект не найден
        </div>
      </AppLayout>
    );
  }

  const files = project.files ?? [];
  const folders = project.folders ?? [];

  return (
    <AppLayout
      breadcrumb={[
        { label: "Главная", href: "/" },
        { label: "Проекты", href: "/projects" },
        { label: project.name },
      ]}
    >
      <div className="mx-auto max-w-5xl space-y-8">
        <div>
          <Link
            href="/projects"
            className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Назад
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            {project.name}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {files.length} файлов · {folders.length} папок
          </p>
        </div>

        {folders.length > 0 && (
          <section>
            <h3 className="mb-3 text-sm font-semibold text-foreground">Папки</h3>
            <div className="scrollbar-quiet flex gap-3 overflow-x-auto pb-1">
              {folders.map((folder) => (
                <div
                  key={folder.id}
                  className="flex min-w-[160px] cursor-pointer items-center gap-2.5 rounded-xl border border-border bg-card px-4 py-3 transition-all hover:border-primary/30 hover:shadow-sm"
                >
                  <Folder className="h-4 w-4 shrink-0 text-primary" />
                  <span className="whitespace-nowrap text-sm font-medium text-foreground">
                    {folder.name}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}

        <section>
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Файлы</h3>
            <div className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
              <button
                onClick={() => setFileView("grid")}
                className={cn(
                  "rounded-md p-1.5 transition-colors",
                  fileView === "grid"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <LayoutGrid className="h-4 w-4" />
              </button>
              <button
                onClick={() => setFileView("list")}
                className={cn(
                  "rounded-md p-1.5 transition-colors",
                  fileView === "list"
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <List className="h-4 w-4" />
              </button>
            </div>
          </div>

          {fileView === "list" && (
            <div className="overflow-hidden rounded-xl border border-border bg-card">
              {files.length === 0 && (
                <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                  Нет файлов в этом проекте
                </div>
              )}
              {files.map((file, i) => (
                <Link
                  key={file.id}
                  href={file.analysis_id ? `/file/${file.id}` : "#"}
                  className={cn(
                    "flex items-center gap-3 px-4 py-3 transition-colors hover:bg-accent",
                    i > 0 && "border-t border-border"
                  )}
                >
                  <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="flex-1 truncate text-sm text-foreground">
                    {file.name}
                  </span>
                  <FileStatusBadge
                    status={file.status}
                    progress={file.progress}
                    riskyScenes={file.analysis?.summary?.risky_scenes ?? null}
                  />
                </Link>
              ))}
            </div>
          )}

          {fileView === "grid" && (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {files.length === 0 && (
                <div className="col-span-full rounded-xl border border-dashed border-border py-10 text-center text-sm text-muted-foreground">
                  Нет файлов в этом проекте
                </div>
              )}
              {files.map((file) => (
                <Link
                  key={file.id}
                  href={file.analysis_id ? `/file/${file.id}` : "#"}
                  className="group rounded-xl border border-border bg-card p-3 transition-all hover:border-primary/30 hover:shadow-sm"
                >
                  <div className="mb-3 flex aspect-video w-full items-center justify-center rounded-lg bg-muted">
                    <Film className="h-6 w-6 text-muted-foreground/60" />
                  </div>
                  <p className="mb-2 truncate text-sm font-medium text-foreground group-hover:text-primary">
                    {file.name}
                  </p>
                  <FileStatusBadge
                    status={file.status}
                    progress={file.progress}
                    riskyScenes={file.analysis?.summary?.risky_scenes ?? null}
                  />
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>
    </AppLayout>
  );
}
