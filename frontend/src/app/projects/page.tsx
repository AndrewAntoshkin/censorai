"use client";

import { AppLayout } from "@/components/layout/app-layout";
import { Search, Folder, Plus, Loader2, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api, type ProjectAPI } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";
import { CreateProjectDialog } from "@/components/projects/create-project-dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.projects
      .list()
      .then((p) => active && setProjects(p))
      .catch(() => {})
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  return (
    <AppLayout breadcrumb={[{ label: "Главная", href: "/" }, { label: "Проекты" }]}>
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="mb-1 text-2xl font-semibold tracking-tight text-foreground">
              Проекты
            </h1>
            <p className="text-sm text-muted-foreground">
              {projects.length} проектов
            </p>
          </div>
          <Button
            variant="outline"
            size="lg"
            className="gap-1.5"
            onClick={() => setCreateOpen(true)}
          >
            <Plus className="h-4 w-4" />
            Новый проект
          </Button>
        </div>

        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Поиск проектов"
            className="h-11 rounded-xl pl-10 text-sm"
          />
        </div>

        {loading ? (
          <div className="flex h-40 items-center justify-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Загрузка…
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {projects.map((project) => (
              <div
                key={project.id}
                className="group relative flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/30 hover:shadow-sm"
              >
                <DropdownMenu>
                  <DropdownMenuTrigger
                    className="absolute bottom-2 right-2 rounded-md p-1 text-muted-foreground opacity-0 transition hover:bg-accent hover:text-foreground group-hover:opacity-100"
                    aria-label="Действия проекта"
                  >
                    <MoreHorizontal className="h-4 w-4" />
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-40">
                    <DropdownMenuItem
                      disabled={renamingId === project.id}
                      onClick={async (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const nextName = window.prompt(
                          "Новое название проекта",
                          project.name
                        );
                        if (nextName == null) return;
                        const trimmed = nextName.trim();
                        if (!trimmed) {
                          window.alert("Название проекта не может быть пустым.");
                          return;
                        }
                        setRenamingId(project.id);
                        try {
                          const updated = await api.projects.rename(project.id, trimmed);
                          setProjects((prev) =>
                            prev.map((p) =>
                              p.id === project.id ? { ...p, name: updated.name } : p
                            )
                          );
                        } catch {
                          window.alert("Не удалось переименовать проект. Попробуйте еще раз.");
                        } finally {
                          setRenamingId(null);
                        }
                      }}
                    >
                      <Pencil className="h-4 w-4" />
                      Переименовать
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      variant="destructive"
                      disabled={deletingId === project.id}
                      onClick={async (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        if (!window.confirm(`Удалить проект «${project.name}»?`)) return;
                        setDeletingId(project.id);
                        try {
                          await api.projects.delete(project.id);
                          setProjects((prev) => prev.filter((p) => p.id !== project.id));
                        } catch (error) {
                          const message = error instanceof Error ? error.message : "";
                          // Проект уже мог быть удален в другой вкладке/сессии.
                          if (message.includes("404")) {
                            setProjects((prev) => prev.filter((p) => p.id !== project.id));
                          } else {
                            window.alert("Не удалось удалить проект. Попробуйте еще раз.");
                          }
                        } finally {
                          setDeletingId(null);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                      Удалить проект
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>

                <Link href={`/project/${project.id}`} className="block">
                  <div className="flex aspect-[5/3] w-full items-center justify-center rounded-lg bg-primary/[0.06]">
                    <Folder className="h-9 w-9 text-primary/70" />
                  </div>
                </Link>
                <Link href={`/project/${project.id}`} className="min-w-0">
                  <span className="block truncate text-sm font-medium text-foreground group-hover:text-primary">
                    {project.name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {project.files_count ?? 0} файлов
                  </span>
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>

      <CreateProjectDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(project) => setProjects((prev) => [project, ...prev])}
      />
    </AppLayout>
  );
}
