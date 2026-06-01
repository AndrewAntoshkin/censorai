"use client";

import { useState, useSyncExternalStore } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { UploadModal } from "@/components/upload/upload-modal";
import { countActiveUploadJobs, subscribeUploadJobs } from "@/lib/upload-jobs";
import { cn } from "@/lib/utils";

interface AppLayoutProps {
  children: React.ReactNode;
  breadcrumb: { label: string; href?: string }[];
  /** Две колонки с независимым скроллом (без прокрутки всего main). */
  splitScroll?: boolean;
}

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export function AppLayout({ children, breadcrumb, splitScroll }: AppLayoutProps) {
  const [uploadOpen, setUploadOpen] = useState(false);
  const activeUploads = useSyncExternalStore(
    subscribeUploadJobs,
    countActiveUploadJobs,
    () => 0
  );

  return (
    <div className="flex h-screen gap-0 bg-sidebar p-1.5">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        {DEMO_MODE && (
          <div className="border-b border-amber-500/20 bg-amber-500/10 px-6 py-2 text-center text-xs text-amber-950 dark:text-amber-100">
            Демо-режим: готовые примеры анализа. Загрузка новых видео недоступна на GitHub Pages.
          </div>
        )}
        <Header
          breadcrumb={breadcrumb}
          onUpload={DEMO_MODE ? undefined : () => setUploadOpen(true)}
          activeUploadCount={DEMO_MODE ? 0 : activeUploads}
        />
        <main
          className={cn(
            "flex-1 scrollbar-quiet px-12 py-8",
            splitScroll
              ? "flex min-h-0 flex-col overflow-hidden"
              : "overflow-y-auto"
          )}
        >
          {children}
        </main>
      </div>
      {!DEMO_MODE && <UploadModal open={uploadOpen} onOpenChange={setUploadOpen} />}
    </div>
  );
}
