"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Home,
  FolderOpen,
  Search,
  Settings,
  ChevronDown,
  ChevronRight,
  ChevronsUpDown,
  Film,
  Folder,
  FileText,
  HelpCircle,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api, type ProjectAPI, type VideoFileAPI } from "@/lib/api";
import { getUploadJobsSnapshot, subscribeUploadJobs } from "@/lib/upload-jobs";

const navItems = [
  { icon: Home, label: "Главная", href: "/" },
  { icon: FolderOpen, label: "Проекты", href: "/projects" },
  { icon: FileText, label: "Отчёты", href: "/reports" },
  { icon: Search, label: "Поиск", href: "/search" },
];

function Widget({
  title,
  count,
  defaultOpen = true,
  children,
}: {
  title: string;
  count?: number;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mb-1">
      <button
        onClick={() => setOpen(!open)}
        className="group/widget flex w-full items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-sidebar-accent"
      >
        {open ? (
          <ChevronDown className="h-3 w-3 shrink-0 opacity-60" />
        ) : (
          <ChevronRight className="h-3 w-3 shrink-0 opacity-60" />
        )}
        <span className="truncate">{title}</span>
        {count !== undefined && (
          <span className="ml-auto text-[11px] tabular-nums opacity-0 transition-opacity group-hover/widget:opacity-60">
            {count}
          </span>
        )}
      </button>
      {open && <div className="mt-0.5 space-y-px pl-1">{children}</div>}
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [recentFiles, setRecentFiles] = useState<VideoFileAPI[]>([]);
  const [readyToasts, setReadyToasts] = useState<Array<{ id: string; fileId: string; name: string }>>(
    []
  );
  const seenDoneJobs = useRef<Set<string>>(new Set());
  const jobs = useSyncExternalStore(
    subscribeUploadJobs,
    getUploadJobsSnapshot,
    getUploadJobsSnapshot
  );

  useEffect(() => {
    let active = true;
    Promise.all([api.projects.list(), api.files.recent(6)])
      .then(([p, r]) => {
        if (!active) return;
        setProjects(p);
        setRecentFiles(r);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const done = jobs.filter((j) => j.status === "done" && j.fileId);
    if (done.length === 0) return;
    const created: Array<{ id: string; fileId: string; name: string }> = [];
    for (const job of done) {
      if (seenDoneJobs.current.has(job.id)) continue;
      seenDoneJobs.current.add(job.id);
      created.push({ id: job.id, fileId: job.fileId!, name: job.file.name });
    }
    if (created.length > 0) {
      setReadyToasts((prev) => [...prev, ...created].slice(-3));
    }
  }, [jobs]);

  const activeReportsCount = jobs.filter((j) =>
    j.status === "uploading" || j.status === "uploaded" || j.status === "analyzing"
  ).length;

  return (
    <aside className="flex h-full w-60 min-w-60 flex-col px-2 pb-1 pt-1.5 text-sidebar-foreground">
      {/* Space switcher */}
      <div className="mb-2 flex items-center gap-1 px-1">
        <Link
          href="/"
          className="group flex min-w-0 flex-1 items-center gap-2 rounded-lg px-1.5 py-1.5 transition-colors hover:bg-sidebar-accent"
        >
          <Image
            src="/logo.png"
            alt="фреймчек"
            width={92}
            height={19}
            priority
            className="shrink-0"
          />
          <ChevronsUpDown className="ml-auto h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        </Link>
        <Link
          href="/settings"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground"
          aria-label="Настройки"
        >
          <Settings className="h-4 w-4" />
        </Link>
      </div>

      {/* Search field */}
      <Link
        href="/search"
        className="mb-3 flex items-center gap-2 rounded-lg border border-transparent bg-sidebar-accent/60 px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent"
      >
        <Search className="h-4 w-4" />
        <span>Поиск</span>
        <kbd className="ml-auto rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
          ⌘K
        </kbd>
      </Link>

      {/* Primary nav */}
      <nav className="space-y-px">
        {navItems
          .filter((i) => i.href !== "/search")
          .map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm transition-colors",
                  isActive
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-sidebar-foreground hover:bg-sidebar-accent"
                )}
              >
                <item.icon
                  className={cn(
                    "h-4 w-4 shrink-0",
                    isActive ? "text-primary" : "text-muted-foreground"
                  )}
                />
                <span>{item.label}</span>
                {item.href === "/reports" && activeReportsCount > 0 && (
                  <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                    <span className="relative inline-flex h-3.5 w-3.5 items-center justify-center">
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    </span>
                    {activeReportsCount}
                  </span>
                )}
              </Link>
            );
          })}
      </nav>

      {/* Widgets */}
      <div className="scrollbar-quiet mt-4 flex-1 overflow-y-auto">
        <Widget title="Проекты" count={projects.length}>
          {projects.slice(0, 5).map((project) => (
            <Link
              key={project.id}
              href={`/project/${project.id}`}
              className={cn(
                "flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm transition-colors",
                pathname === `/project/${project.id}`
                  ? "bg-sidebar-accent font-medium text-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent"
              )}
            >
              <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{project.name}</span>
            </Link>
          ))}
        </Widget>

        <Widget title="Недавние" count={recentFiles.length}>
          {recentFiles.map((file) => (
            <Link
              key={file.id}
              href={`/file/${file.id}`}
              className={cn(
                "flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm transition-colors",
                pathname === `/file/${file.id}`
                  ? "bg-sidebar-accent font-medium text-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent"
              )}
            >
              <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="truncate">{file.name}</span>
            </Link>
          ))}
        </Widget>
      </div>

      {/* Footer: profile + help */}
      <div className="mt-1 flex items-center gap-1 border-t border-sidebar-border pt-2">
        <button className="group flex min-w-0 flex-1 items-center gap-2 rounded-lg px-1.5 py-1.5 text-left transition-colors hover:bg-sidebar-accent">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/12 text-xs font-semibold text-primary">
            А
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-foreground">
              Аркадий Н.
            </span>
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        </button>
        <Link
          href="/help"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground"
          aria-label="Помощь"
        >
          <HelpCircle className="h-4 w-4" />
        </Link>
      </div>

      <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[320px] flex-col gap-2">
        {readyToasts.map((toast) => (
          <div
            key={toast.id}
            className="pointer-events-auto rounded-xl border border-border bg-card p-3 shadow-lg"
          >
            <p className="text-sm font-medium text-foreground">Отчёт готов</p>
            <p className="mt-0.5 truncate text-xs text-muted-foreground">{toast.name}</p>
            <div className="mt-2 flex justify-end gap-2">
              <button
                type="button"
                onClick={() =>
                  setReadyToasts((prev) => prev.filter((x) => x.id !== toast.id))
                }
                className="rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                Закрыть
              </button>
              <Link
                href={`/file/${toast.fileId}`}
                onClick={() =>
                  setReadyToasts((prev) => prev.filter((x) => x.id !== toast.id))
                }
                className="rounded-md bg-primary px-2.5 py-1 text-xs font-medium text-primary-foreground hover:opacity-90"
              >
                Смотреть
              </Link>
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
