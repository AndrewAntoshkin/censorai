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
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useWorkspace } from "@/contexts/workspace-context";
import {
  getUploadJobsSnapshot,
  markUploadJobNotified,
  subscribeUploadJobs,
} from "@/lib/upload-jobs";
import { useAuth } from "@/contexts/auth-context";
import { OrgSwitcher } from "@/components/layout/org-switcher";

const navItems = [
  { icon: Home, label: "Главная", href: "/" },
  { icon: FolderOpen, label: "Проекты", href: "/projects" },
  { icon: FileText, label: "Отчёты", href: "/reports" },
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

function profileInitials(name: string): string {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function Sidebar({ onSearch }: { onSearch?: () => void }) {
  const pathname = usePathname();
  const { user, loading: authLoading } = useAuth();
  const { projects, recentFiles, inProgressCount: backendInProgressCount } = useWorkspace();
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
    // Skip jobs whose toast was already dismissed (persisted in the store, so
    // it survives sidebar remounts on navigation — e.g. after clicking «Смотреть»).
    const done = jobs.filter((j) => j.status === "done" && j.fileId && !j.notified);
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

  const dismissToast = (id: string) => {
    markUploadJobNotified(id);
    setReadyToasts((prev) => prev.filter((x) => x.id !== id));
  };

  const localPreRegisterCount = jobs.filter(
    (j) =>
      (j.status === "uploading" || j.status === "uploaded" || j.status === "analyzing") &&
      !j.fileId
  ).length;
  const activeReportsCount = backendInProgressCount + localPreRegisterCount;
  const isSuperAdmin = user?.role === "super_admin";

  return (
    <aside className="flex h-full w-60 min-w-60 flex-col px-2 pb-1 pt-1.5 text-sidebar-foreground">
      {/* Logo / org switcher (super admin) */}
      <div className="mb-2 flex items-center gap-1 px-1">
        {isSuperAdmin ? (
          <OrgSwitcher />
        ) : (
          <Link
            href="/"
            className="flex min-w-0 flex-1 items-center rounded-lg px-1.5 py-1.5 transition-colors hover:bg-sidebar-accent"
          >
            <Image
              src="/logo.png"
              alt="фреймчек"
              width={92}
              height={19}
              priority
              className="shrink-0"
            />
          </Link>
        )}
        <Link
          href="/settings"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground"
          aria-label="Настройки"
        >
          <Settings className="h-4 w-4" />
        </Link>
      </div>

      {/* Search field */}
      <button
        type="button"
        onClick={onSearch}
        className="mb-3 flex w-full items-center gap-2 rounded-lg border border-transparent bg-sidebar-accent/60 px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent"
      >
        <Search className="h-4 w-4" />
        <span>Поиск</span>
        <kbd className="ml-auto rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
          ⌘K
        </kbd>
      </button>

      {/* Primary nav */}
      <nav className="space-y-px">
        {navItems.map((item) => {
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
        {user?.role === "super_admin" && (
          <Link
            href="/ops"
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-sm transition-colors",
              pathname === "/ops"
                ? "bg-primary/10 font-medium text-primary"
                : "text-sidebar-foreground hover:bg-sidebar-accent"
            )}
          >
            <Activity
              className={cn(
                "h-4 w-4 shrink-0",
                pathname === "/ops" ? "text-primary" : "text-muted-foreground"
              )}
            />
            <span>Операции</span>
          </Link>
        )}
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
          {recentFiles.slice(0, 6).map((file) => (
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
        <Link
          href={user ? "/profile" : "/login"}
          className="group flex min-w-0 flex-1 items-center gap-2 rounded-lg px-1.5 py-1.5 text-left transition-colors hover:bg-sidebar-accent"
        >
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/12 text-xs font-semibold text-primary">
            {user ? profileInitials(user.display_name) : "?"}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-foreground">
              {authLoading
                ? "…"
                : user
                  ? user.display_name
                  : "Войти"}
            </span>
          </span>
          <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        </Link>
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
                onClick={() => dismissToast(toast.id)}
                className="rounded-md px-2 py-1 text-xs text-muted-foreground hover:bg-accent hover:text-foreground"
              >
                Закрыть
              </button>
              <Link
                href={`/file/${toast.fileId}`}
                onClick={() => dismissToast(toast.id)}
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
