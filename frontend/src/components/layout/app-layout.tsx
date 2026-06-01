"use client";

import { useState } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { UploadModal } from "@/components/upload/upload-modal";

interface AppLayoutProps {
  children: React.ReactNode;
  breadcrumb: { label: string; href?: string }[];
}

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

export function AppLayout({ children, breadcrumb }: AppLayoutProps) {
  const [uploadOpen, setUploadOpen] = useState(false);

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
        />
        <main className="flex-1 overflow-y-auto scrollbar-quiet px-8 py-8">
          {children}
        </main>
      </div>
      {!DEMO_MODE && <UploadModal open={uploadOpen} onOpenChange={setUploadOpen} />}
    </div>
  );
}
