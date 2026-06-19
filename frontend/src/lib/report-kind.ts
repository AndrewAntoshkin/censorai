import type { VideoFileAPI } from "@/lib/api";

export function resolveReportKind(
  file: Pick<VideoFileAPI, "report_kind"> & {
    analysis?: { summary?: { report_kind?: string } | null } | null;
  }
): "moderation" | "placement" {
  const kind =
    file.report_kind ?? file.analysis?.summary?.report_kind ?? "moderation";
  return kind === "placement" ? "placement" : "moderation";
}

export function reportTypeLabel(file: Parameters<typeof resolveReportKind>[0]): string {
  return resolveReportKind(file) === "placement" ? "Продакт плейсмент" : "Анализ";
}
