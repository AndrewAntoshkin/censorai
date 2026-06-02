"use client";

import { AppLayout } from "@/components/layout/app-layout";
import { Search, Folder, Plus, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api, type ProjectAPI } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";
import { CreateProjectDialog } from "@/components/projects/create-project-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameProjectId, setRenameProjectId] = useState<string | null>(null);
  const [renameName, setRenameName] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);

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

  const openRenameDialog = (project: ProjectAPI) => {
    setRenameProjectId(project.id);
    setRenameName(project.name);
    setRenameError(null);
    setRenameOpen(true);
  };

  const closeRenameDialog = () => {
    setRenameOpen(false);
    setRenameProjectId(null);
    setRenameName("");
    setRenameError(null);
  };

  const submitRename = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renameProjectId) return;
    const trimmed = renameName.trim();
    if (!trimmed) {
      setRenameError("Название проекта не может быть пустым.");
      return;
    }
    setRenamingId(renameProjectId);
    setRenameError(null);
    try {
      const updated = await api.projects.rename(renameProjectId, trimmed);
      setProjects((prev) =>
        prev.map((p) => (p.id === renameProjectId ? { ...p, name: updated.name } : p))
      );
      closeRenameDialog();
    } catch {
      setRenameError("Не удалось переименовать проект. Попробуйте еще раз.");
    } finally {
      setRenamingId(null);
    }
  };

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
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4"
              >
                <Skeleton className="aspect-[5/3] w-full rounded-lg" />
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-4 w-1/3" />
              </div>
            ))}
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
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        openRenameDialog(project);
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

      <Dialog open={renameOpen} onOpenChange={(next) => !renamingId && !next && closeRenameDialog()}>
        <DialogContent className="sm:max-w-md">
          <form onSubmit={submitRename}>
            <DialogHeader>
              <DialogTitle>Переименовать проект</DialogTitle>
              <DialogDescription>Введите новое название проекта.</DialogDescription>
            </DialogHeader>
            <div className="py-2">
              <Input
                value={renameName}
                onChange={(e) => setRenameName(e.target.value)}
                placeholder="Название проекта"
                autoFocus
                disabled={!!renamingId}
                className="h-10"
              />
              {renameError && <p className="mt-2 text-xs text-critical">{renameError}</p>}
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={closeRenameDialog}
                disabled={!!renamingId}
              >
                Отмена
              </Button>
              <Button type="submit" disabled={!!renamingId || !renameName.trim()}>
                {renamingId ? "Сохраняем…" : "Сохранить"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}
