"use client";

import { useEffect, useState } from "react";
import { AppLayout } from "@/components/layout/app-layout";
import { ReportsTable } from "@/components/reports/reports-table";
import { api, type VideoFileAPI } from "@/lib/api";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { getUploadJobsSnapshot, subscribeUploadJobs } from "@/lib/upload-jobs";

const REPORTS_LIMIT = 100;
const WORKING_STATUSES = new Set(["uploading", "uploaded", "analyzing"]);

export default function ReportsPage() {
  const [reports, setReports] = useState<VideoFileAPI[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"all" | "in_progress">("all");
  const [localInFlightCount, setLocalInFlightCount] = useState(0);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const list = await api.files.recent(REPORTS_LIMIT, { analyzedOnly: false });
        if (active) setReports(list);
      } catch {
        // noop
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    const poll = window.setInterval(() => {
      void load();
    }, 5000);
    return () => {
      active = false;
      window.clearInterval(poll);
    };
  }, []);

  useEffect(() => {
    const update = () => {
      const jobs = getUploadJobsSnapshot();
      setLocalInFlightCount(
        jobs.filter(
          (j) =>
            ["uploading", "uploaded", "analyzing"].includes(j.status) &&
            !j.fileId
        ).length
      );
    };
    update();
    return subscribeUploadJobs(update);
  }, []);

  const handleProjectAssigned = (fileId: string, projectId: string) => {
    setReports((prev) =>
      prev.map((f) => (f.id === fileId ? { ...f, project_id: projectId } : f))
    );
  };

  const inProgressCount = reports.filter((f) =>
    WORKING_STATUSES.has((f.status || "").toLowerCase())
  ).length + localInFlightCount;

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
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Skeleton className="h-9 w-20" />
              <Skeleton className="h-9 w-28" />
            </div>
            <Skeleton className="h-11 w-full rounded-xl" />
            <div className="rounded-xl border border-border bg-card p-4">
              <div className="space-y-3">
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
                <Skeleton className="h-10 w-full" />
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <Tabs
              value={activeTab}
              onValueChange={(v) => setActiveTab((v as "all" | "in_progress") || "all")}
            >
              <TabsList variant="line" className="h-9">
                <TabsTrigger value="all">Все</TabsTrigger>
                <TabsTrigger value="in_progress">В работе ({inProgressCount})</TabsTrigger>
              </TabsList>
            </Tabs>
            <ReportsTable
              files={reports}
              statusFilter={activeTab}
              onProjectAssigned={handleProjectAssigned}
              onFilesChanged={setReports}
              emptyMessage={
                activeTab === "in_progress"
                  ? "Сейчас нет отчётов в работе."
                  : "Пока нет готовых отчётов. Загрузите видео и дождитесь анализа."
              }
            />
            {activeTab === "in_progress" && localInFlightCount > 0 && (
              <p className="text-xs text-muted-foreground">
                Идёт загрузка на сервер: {localInFlightCount}{" "}
                {localInFlightCount === 1 ? "файл" : "файла"}.
              </p>
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
