import { cn } from "@/lib/utils";

interface FileStatusBadgeProps {
  status: string;
  progress?: number;
  /** number of risky scenes when analyzed; null/undefined if unknown */
  riskyScenes?: number | null;
  /** number of fragments the model could not analyze (manual review needed) */
  reviewCount?: number | null;
  reportKind?: "moderation" | "placement";
  className?: string;
}

const base =
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium";

export function FileStatusBadge({
  status,
  progress,
  riskyScenes,
  reviewCount,
  reportKind,
  className,
}: FileStatusBadgeProps) {
  if (status === "processing" || status === "analyzing") {
    return (
      <span className={cn(base, "bg-primary/10 text-primary", className)}>
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
        Анализ{progress ? ` ${progress}%` : "…"}
      </span>
    );
  }

  if (status === "queued") {
    return (
      <span className={cn(base, "bg-muted text-muted-foreground", className)}>
        В очереди
      </span>
    );
  }

  if (status === "uploading") {
    return (
      <span className={cn(base, "bg-warning-soft text-warning", className)}>
        Загрузка
      </span>
    );
  }

  if (status === "error") {
    return (
      <span className={cn(base, "bg-critical-soft text-critical", className)}>
        Ошибка
      </span>
    );
  }

  // analyzed / completed
  if (status === "analyzed" || status === "completed" || riskyScenes != null) {
    if (reportKind === "placement") {
      if (riskyScenes && riskyScenes > 0) {
        return (
          <span className={cn(base, "bg-primary/10 text-primary", className)}>
            {riskyScenes} слотов
          </span>
        );
      }
      return (
        <span className={cn(base, "bg-muted text-muted-foreground", className)}>
          Слотов нет
        </span>
      );
    }
    if (reviewCount && reviewCount > 0) {
      return (
        <span className={cn(base, "bg-warning-soft text-warning", className)}>
          Требует проверки
        </span>
      );
    }
    if (riskyScenes && riskyScenes > 0) {
      return (
        <span className={cn(base, "bg-critical-soft text-critical", className)}>
          {riskyScenes} нарушений
        </span>
      );
    }
    return (
      <span className={cn(base, "bg-success-soft text-success", className)}>
        Нарушений нет
      </span>
    );
  }

  return (
    <span className={cn(base, "bg-muted text-muted-foreground", className)}>
      Не проверен
    </span>
  );
}
