"use client";

import { useEffect, useState } from "react";
import { FolderPlus, Loader2, MoreHorizontal, Trash2 } from "lucide-react";
import { api, type ProjectAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CreateProjectDialog } from "@/components/projects/create-project-dialog";
import { cn } from "@/lib/utils";

interface AddToProjectMenuProps {
  fileId: string;
  currentProjectId?: string | null;
  onAssigned?: (projectId: string) => void;
  onDelete?: () => Promise<void> | void;
  className?: string;
}

export function AddToProjectMenu({
  fileId,
  currentProjectId,
  onAssigned,
  onDelete,
  className,
}: AddToProjectMenuProps) {
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [loading, setLoading] = useState(false);
  const [assigningId, setAssigningId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true);
    api.projects
      .list()
      .then((list) => active && setProjects(list))
      .catch(() => {})
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [open]);

  const assign = async (projectId: string) => {
    if (projectId === currentProjectId) {
      setOpen(false);
      return;
    }
    setAssigningId(projectId);
    try {
      await api.files.assignToProject(fileId, projectId);
      onAssigned?.(projectId);
      setOpen(false);
    } catch {
      // keep menu open on error
    } finally {
      setAssigningId(null);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    if (!window.confirm("Удалить этот отчёт?")) return;
    setDeleting(true);
    try {
      await onDelete();
      setOpen(false);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <DropdownMenu open={open} onOpenChange={setOpen}>
        <DropdownMenuTrigger
          render={
            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              className={cn("relative z-10 shrink-0 text-muted-foreground", className)}
              aria-label="Действия"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          }
        />
        <DropdownMenuContent align="end" className="z-50 w-52">
          <DropdownMenuGroup>
            <DropdownMenuLabel>Добавить в проект</DropdownMenuLabel>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          {loading && (
            <DropdownMenuItem disabled>
              <Loader2 className="h-4 w-4 animate-spin" />
              Загрузка…
            </DropdownMenuItem>
          )}
          {!loading && projects.length === 0 && (
            <DropdownMenuItem disabled>Нет проектов</DropdownMenuItem>
          )}
          {projects.map((project) => (
            <DropdownMenuItem
              key={project.id}
              disabled={assigningId !== null}
              onClick={(e) => {
                e.stopPropagation();
                void assign(project.id);
              }}
            >
              {assigningId === project.id ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : null}
              <span className="truncate">{project.name}</span>
              {project.id === currentProjectId && (
                <span className="ml-auto text-xs text-muted-foreground">текущий</span>
              )}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem
            disabled={assigningId !== null || deleting}
            onClick={(e) => {
              e.stopPropagation();
              setOpen(false);
              setCreateOpen(true);
            }}
          >
            <FolderPlus className="h-4 w-4" />
            Новый проект…
          </DropdownMenuItem>
          {onDelete && (
            <>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                disabled={assigningId !== null || deleting}
                onClick={(e) => {
                  e.stopPropagation();
                  void handleDelete();
                }}
                className="text-critical focus:text-critical"
              >
                {deleting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                Удалить отчёт
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <CreateProjectDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={(project) => {
          setProjects((prev) => [project, ...prev]);
          void assign(project.id);
        }}
      />
    </>
  );
}
