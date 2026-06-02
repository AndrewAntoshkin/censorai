"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { AppLayout } from "@/components/layout/app-layout";
import { ReportsTable } from "@/components/reports/reports-table";
import { api, type VideoFileAPI } from "@/lib/api";

const REPORTS_LIMIT = 100;

export default function ReportsPage() {
  const [reports, setReports] = useState<VideoFileAPI[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api.files
      .recent(REPORTS_LIMIT)
      .then((list) => active && setReports(list))
      .catch(() => {})
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const handleProjectAssigned = (fileId: string, projectId: string) => {
    setReports((prev) =>
      prev.map((f) => (f.id === fileId ? { ...f, project_id: projectId } : f))
    );
  };

  return (
    <AppLayout breadcrumb={[{ label: "Главная", href: "/" }, { label: "Отчёты" }]}>
      <div className="mx-auto max-w-5xl space-y-8">
        <div>
          <h1 className="mb-1 text-2xl font-semibold tracking-tight text-foreground">
            Отчёты
          </h1>
          <p className="text-sm text-muted-foreground">
            {loading
              ? "Загрузка…"
              : `${reports.length} ${reports.length === 1 ? "отчёт" : reports.length < 5 ? "отчёта" : "отчётов"}`}
          </p>
        </div>

        {loading ? (
          <div className="flex h-40 items-center justify-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Загрузка…
          </div>
        ) : (
          <ReportsTable
            files={reports}
            onProjectAssigned={handleProjectAssigned}
            onFilesChanged={setReports}
            emptyMessage="Пока нет готовых отчётов. Загрузите видео и дождитесь анализа."
          />
        )}
      </div>
    </AppLayout>
  );
}
