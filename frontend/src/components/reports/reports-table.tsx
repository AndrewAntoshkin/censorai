"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Film, Search, Trash2 } from "lucide-react";
import { cn, displayFileName } from "@/lib/utils";
import { api, type ProjectAPI, type VideoFileAPI } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FileStatusBadge } from "@/components/shared/file-status-badge";
import { AddToProjectMenu } from "@/components/projects/add-to-project-menu";

const PAGE_SIZE = 10;

interface ReportsTableProps {
  files: VideoFileAPI[];
  statusFilter?: "all" | "in_progress";
  emptyMessage?: string;
  onProjectAssigned?: (fileId: string, projectId: string) => void;
  onFilesChanged?: (files: VideoFileAPI[]) => void;
  className?: string;
}

const WORKING_STATUSES = new Set(["uploading", "uploaded", "analyzing"]);

function formatReportDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

export function ReportsTable({
  files,
  statusFilter = "all",
  emptyMessage = "Пока нет готовых отчётов",
  onProjectAssigned,
  onFilesChanged,
  className,
}: ReportsTableProps) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [bulkProjectId, setBulkProjectId] = useState("");
  const [busyAction, setBusyAction] = useState<"assign" | "delete" | null>(null);

  useEffect(() => {
    let active = true;
    api.projects
      .list()
      .then((items) => active && setProjects(items))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    setSelectedIds((prev) => {
      const next = new Set<string>();
      for (const id of prev) {
        if (files.some((f) => f.id === id)) next.add(id);
      }
      return next;
    });
  }, [files]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const base =
      statusFilter === "in_progress"
        ? files.filter((f) => WORKING_STATUSES.has((f.status || "").toLowerCase()))
        : files;
    if (!q) return base;
    return base.filter((f) => displayFileName(f.name).toLowerCase().includes(q));
  }, [files, query, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

  useEffect(() => {
    setPage(1);
  }, [query]);

  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  const pageItems = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return filtered.slice(start, start + PAGE_SIZE);
  }, [filtered, page]);
  const pageSelectedCount = pageItems.filter((f) => selectedIds.has(f.id)).length;
  const allPageSelected = pageItems.length > 0 && pageSelectedCount === pageItems.length;

  const toggleRow = (fileId: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(fileId);
      else next.delete(fileId);
      return next;
    });
  };

  const togglePage = (checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      for (const item of pageItems) {
        if (checked) next.add(item.id);
        else next.delete(item.id);
      }
      return next;
    });
  };

  const handleBulkAssign = async () => {
    if (!bulkProjectId || selectedIds.size === 0) return;
    setBusyAction("assign");
    try {
      await Promise.all(
        [...selectedIds].map((fileId) => api.files.assignToProject(fileId, bulkProjectId))
      );
      const next = files.map((file) =>
        selectedIds.has(file.id) ? { ...file, project_id: bulkProjectId } : file
      );
      onFilesChanged?.(next);
      setSelectedIds(new Set());
      setBulkProjectId("");
    } finally {
      setBusyAction(null);
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Удалить выбранные отчёты (${selectedIds.size})?`)) return;
    setBusyAction("delete");
    try {
      await Promise.all([...selectedIds].map((fileId) => api.files.delete(fileId)));
      const next = files.filter((file) => !selectedIds.has(file.id));
      onFilesChanged?.(next);
      setSelectedIds(new Set());
    } finally {
      setBusyAction(null);
    }
  };

  const handleSingleDelete = async (fileId: string) => {
    await api.files.delete(fileId);
    const next = files.filter((file) => file.id !== fileId);
    onFilesChanged?.(next);
    setSelectedIds((prev) => {
      const nextSelected = new Set(prev);
      nextSelected.delete(fileId);
      return nextSelected;
    });
  };

  const rangeStart = filtered.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const rangeEnd = Math.min(page * PAGE_SIZE, filtered.length);

  if (files.length === 0) {
    return (
      <div
        className={cn(
          "rounded-xl border border-border bg-card px-4 py-10 text-center text-sm text-muted-foreground",
          className
        )}
      >
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Поиск по названию отчёта"
          className="h-11 rounded-xl pl-10 text-sm"
        />
      </div>

      {selectedIds.size > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card px-3 py-2">
          <span className="text-xs text-muted-foreground">Выбрано: {selectedIds.size}</span>
          <select
            value={bulkProjectId}
            onChange={(e) => setBulkProjectId(e.target.value)}
            className="h-8 rounded-md border border-border bg-background px-2 text-xs"
          >
            <option value="">Выберите проект</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          <Button
            size="sm"
            variant="outline"
            disabled={!bulkProjectId || busyAction !== null}
            onClick={() => void handleBulkAssign()}
          >
            В проект
          </Button>
          <Button
            size="sm"
            variant="destructive"
            disabled={busyAction !== null}
            onClick={() => void handleBulkDelete()}
          >
            <Trash2 className="mr-1 h-3.5 w-3.5" />
            Удалить
          </Button>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <div>
          <table className="w-full table-fixed border-collapse text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-left text-xs font-medium text-muted-foreground">
                <th className="w-10 px-2 py-3 text-center">
                  <input
                    type="checkbox"
                    checked={allPageSelected}
                    onChange={(e) => togglePage(e.target.checked)}
                    aria-label="Выбрать все на странице"
                  />
                </th>
                <th className="px-4 py-3 font-medium">Название</th>
                <th className="hidden w-28 px-4 py-3 font-medium md:table-cell">
                  Дата
                </th>
                <th className="w-36 px-4 py-3 font-medium">Статус</th>
                <th className="w-12 px-2 py-3" aria-label="Действия" />
              </tr>
            </thead>
            <tbody>
              {pageItems.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    className="px-4 py-10 text-center text-sm text-muted-foreground"
                  >
                    Ничего не найдено
                  </td>
                </tr>
              ) : (
                pageItems.map((file) => {
                  const isInProgress = WORKING_STATUSES.has((file.status || "").toLowerCase());
                  return (
                    <tr
                      key={file.id}
                      className="border-b border-border last:border-0 transition-colors hover:bg-accent/50"
                    >
                      <td className="px-2 py-3 text-center">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(file.id)}
                          onChange={(e) => toggleRow(file.id, e.target.checked)}
                          aria-label={`Выбрать ${displayFileName(file.name)}`}
                        />
                      </td>
                      <td className="px-4 py-3">
                        {isInProgress ? (
                          <div
                            className="flex min-w-0 max-w-full cursor-not-allowed items-center gap-2.5 font-medium text-muted-foreground"
                            title="В работе"
                          >
                            <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <span className="block min-w-0 truncate">{displayFileName(file.name)}</span>
                          </div>
                        ) : (
                          <Link
                            href={`/file/${file.id}`}
                            className="flex min-w-0 max-w-full items-center gap-2.5 font-medium text-foreground hover:text-primary"
                            title={displayFileName(file.name)}
                          >
                            <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <span className="block min-w-0 truncate">{displayFileName(file.name)}</span>
                          </Link>
                        )}
                      </td>
                      <td className="hidden truncate px-4 py-3 text-muted-foreground md:table-cell">
                        {formatReportDate(file.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        <FileStatusBadge
                          status={file.status}
                          progress={file.progress}
                          riskyScenes={file.analysis?.summary?.risky_scenes ?? null}
                        />
                      </td>
                      <td className="px-2 py-3 text-right">
                        <AddToProjectMenu
                          fileId={file.id}
                          currentProjectId={file.project_id}
                          onAssigned={(projectId) => onProjectAssigned?.(file.id, projectId)}
                          onDelete={() => handleSingleDelete(file.id)}
                        />
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {filtered.length > 0 && (
          <div className="flex flex-col gap-3 border-t border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-xs text-muted-foreground">
              {rangeStart}–{rangeEnd} из {filtered.length}
              {query.trim() ? ` (всего отчётов: ${files.length})` : ""}
            </p>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
                Назад
              </Button>
              <span className="min-w-[5rem] text-center text-xs text-muted-foreground">
                {page} / {totalPages}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Вперёд
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
