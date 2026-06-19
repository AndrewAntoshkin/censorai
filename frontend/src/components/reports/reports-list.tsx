"use client";

import Link from "next/link";
import { Film } from "lucide-react";
import { cn } from "@/lib/utils";
import type { VideoFileAPI } from "@/lib/api";
import { FileStatusBadge } from "@/components/shared/file-status-badge";
import { AddToProjectMenu } from "@/components/projects/add-to-project-menu";

interface ReportsListProps {
  files: VideoFileAPI[];
  emptyMessage?: string;
  onProjectAssigned?: (fileId: string, projectId: string) => void;
  className?: string;
}

const WORKING_STATUSES = new Set(["uploading", "uploaded", "analyzing"]);

export function ReportsList({
  files,
  emptyMessage = "Пока нет готовых отчётов",
  onProjectAssigned,
  className,
}: ReportsListProps) {
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
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-card",
        className
      )}
    >
      {files.map((file, i) => (
        (() => {
          const isInProgress = WORKING_STATUSES.has((file.status || "").toLowerCase());
          return (
        <div
          key={file.id}
          className={cn(
            "flex items-center gap-2 px-4 py-3 transition-colors hover:bg-accent",
            i > 0 && "border-t border-border"
          )}
        >
          {isInProgress ? (
            <div
              className="flex min-w-0 flex-1 cursor-not-allowed items-center gap-3"
              title="В работе"
            >
              <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate text-sm text-muted-foreground">{file.name}</span>
              <FileStatusBadge
                status={file.status}
                progress={file.progress}
                riskyScenes={file.analysis?.summary?.risky_scenes ?? null}
                reviewCount={file.analysis?.summary?.review_count ?? null}
                reportKind={file.analysis?.summary?.report_kind}
                className="ml-auto shrink-0"
              />
            </div>
          ) : (
            <Link
              href={`/file/${file.id}`}
              className="flex min-w-0 flex-1 items-center gap-3"
            >
              <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate text-sm text-foreground">{file.name}</span>
              <FileStatusBadge
                status={file.status}
                progress={file.progress}
                riskyScenes={file.analysis?.summary?.risky_scenes ?? null}
                reviewCount={file.analysis?.summary?.review_count ?? null}
                reportKind={file.analysis?.summary?.report_kind}
                className="ml-auto shrink-0"
              />
            </Link>
          )}
          <AddToProjectMenu
            fileId={file.id}
            currentProjectId={file.project_id}
            onAssigned={(projectId) => onProjectAssigned?.(file.id, projectId)}
          />
        </div>
          );
        })()
      ))}
    </div>
  );
}
