"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Film, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import type { VideoFileAPI } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FileStatusBadge } from "@/components/shared/file-status-badge";
import { AddToProjectMenu } from "@/components/projects/add-to-project-menu";

const PAGE_SIZE = 10;

interface ReportsTableProps {
  files: VideoFileAPI[];
  emptyMessage?: string;
  onProjectAssigned?: (fileId: string, projectId: string) => void;
  className?: string;
}

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
  emptyMessage = "Пока нет готовых отчётов",
  onProjectAssigned,
  className,
}: ReportsTableProps) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return files;
    return files.filter((f) => f.name.toLowerCase().includes(q));
  }, [files, query]);

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

      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-left text-xs font-medium text-muted-foreground">
                <th className="px-4 py-3 font-medium">Название</th>
                <th className="hidden w-28 px-4 py-3 font-medium sm:table-cell">
                  Дата
                </th>
                <th className="w-40 px-4 py-3 font-medium">Статус</th>
                <th className="w-12 px-2 py-3" aria-label="Действия" />
              </tr>
            </thead>
            <tbody>
              {pageItems.length === 0 ? (
                <tr>
                  <td
                    colSpan={4}
                    className="px-4 py-10 text-center text-sm text-muted-foreground"
                  >
                    Ничего не найдено
                  </td>
                </tr>
              ) : (
                pageItems.map((file) => (
                  <tr
                    key={file.id}
                    className="border-b border-border last:border-0 transition-colors hover:bg-accent/50"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/file/${file.id}`}
                        className="flex min-w-0 items-center gap-2.5 font-medium text-foreground hover:text-primary"
                      >
                        <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <span className="truncate">{file.name}</span>
                      </Link>
                    </td>
                    <td className="hidden px-4 py-3 text-muted-foreground sm:table-cell">
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
                        onAssigned={(projectId) =>
                          onProjectAssigned?.(file.id, projectId)
                        }
                      />
                    </td>
                  </tr>
                ))
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
