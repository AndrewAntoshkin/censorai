"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";
import { Search, Folder, Film, Loader2, CornerDownLeft } from "lucide-react";
import { api, type ProjectAPI, type VideoFileAPI } from "@/lib/api";
import { cn } from "@/lib/utils";

type ResultItem =
  | { kind: "project"; id: string; name: string; href: string }
  | { kind: "file"; id: string; name: string; href: string; status: string };

const DEBOUNCE_MS = 180;

export function SearchModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [files, setFiles] = useState<VideoFileAPI[]>([]);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(0);
  const listRef = useRef<HTMLDivElement>(null);

  // Flat list for keyboard navigation (projects first, then files).
  const items = useMemo<ResultItem[]>(() => {
    const p: ResultItem[] = projects.map((proj) => ({
      kind: "project",
      id: proj.id,
      name: proj.name,
      href: `/project/${proj.id}`,
    }));
    const f: ResultItem[] = files.map((file) => ({
      kind: "file",
      id: file.id,
      name: file.name,
      href: `/file/${file.id}`,
      status: file.status,
    }));
    return [...p, ...f];
  }, [projects, files]);

  // Reset state whenever the modal is reopened.
  useEffect(() => {
    if (open) {
      setQuery("");
      setProjects([]);
      setFiles([]);
      setActive(0);
    }
  }, [open]);

  // Debounced search.
  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setProjects([]);
      setFiles([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const res = await api.search(q);
        if (controller.signal.aborted) return;
        setProjects(res.projects ?? []);
        setFiles(res.files ?? []);
        setActive(0);
      } catch {
        if (!controller.signal.aborted) {
          setProjects([]);
          setFiles([]);
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [query]);

  const go = useCallback(
    (item: ResultItem) => {
      onOpenChange(false);
      router.push(item.href);
    },
    [onOpenChange, router]
  );

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % items.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i - 1 + items.length) % items.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const item = items[active];
      if (item) go(item);
    }
  };

  // Keep the active row scrolled into view.
  useEffect(() => {
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${active}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  const q = query.trim();
  const hasResults = items.length > 0;

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Backdrop className="fixed inset-0 z-50 bg-black/30 supports-backdrop-filter:backdrop-blur-xs data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0" />
        <DialogPrimitive.Popup
          className="fixed left-1/2 top-[14vh] z-50 w-full max-w-xl -translate-x-1/2 overflow-hidden rounded-2xl bg-popover text-popover-foreground shadow-2xl ring-1 ring-foreground/10 outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95"
        >
          <DialogPrimitive.Title className="sr-only">
            Поиск по проектам и отчётам
          </DialogPrimitive.Title>

          {/* Search input */}
          <div className="flex items-center gap-3 border-b border-border px-4">
            {loading ? (
              <Loader2 className="h-5 w-5 shrink-0 animate-spin text-muted-foreground" />
            ) : (
              <Search className="h-5 w-5 shrink-0 text-muted-foreground" />
            )}
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Поиск по проектам и отчётам…"
              className="h-14 flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground"
            />
            <kbd className="hidden shrink-0 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground sm:block">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div ref={listRef} className="max-h-[50vh] overflow-y-auto scrollbar-quiet p-2">
            {!q && (
              <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                Начните вводить название проекта или файла
              </p>
            )}
            {q && !loading && !hasResults && (
              <p className="px-3 py-6 text-center text-sm text-muted-foreground">
                Ничего не найдено по «{q}»
              </p>
            )}

            {projects.length > 0 && (
              <Group label="Проекты">
                {projects.map((proj, i) => (
                  <Row
                    key={proj.id}
                    idx={i}
                    active={active === i}
                    onMouseEnter={() => setActive(i)}
                    onClick={() => go(items[i])}
                  >
                    <Folder className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="truncate">{proj.name}</span>
                  </Row>
                ))}
              </Group>
            )}

            {files.length > 0 && (
              <Group label="Отчёты">
                {files.map((file, i) => {
                  const idx = projects.length + i;
                  return (
                    <Row
                      key={file.id}
                      idx={idx}
                      active={active === idx}
                      onMouseEnter={() => setActive(idx)}
                      onClick={() => go(items[idx])}
                    >
                      <Film className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <span className="truncate">{file.name}</span>
                      <StatusDot status={file.status} />
                    </Row>
                  );
                })}
              </Group>
            )}
          </div>

          {/* Footer hint */}
          {hasResults && (
            <div className="flex items-center gap-4 border-t border-border px-4 py-2 text-[11px] text-muted-foreground">
              <span className="flex items-center gap-1">
                <CornerDownLeft className="h-3 w-3" /> открыть
              </span>
              <span>↑↓ навигация</span>
              <span>esc закрыть</span>
            </div>
          )}
        </DialogPrimitive.Popup>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

function Group({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-1">
      <p className="px-3 pb-1 pt-2 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <div className="space-y-px">{children}</div>
    </div>
  );
}

function Row({
  idx,
  active,
  onMouseEnter,
  onClick,
  children,
}: {
  idx: number;
  active: boolean;
  onMouseEnter: () => void;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      data-idx={idx}
      onMouseEnter={onMouseEnter}
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-left text-sm transition-colors",
        active ? "bg-primary/10 text-foreground" : "text-foreground hover:bg-accent"
      )}
    >
      {children}
    </button>
  );
}

function StatusDot({ status }: { status: string }) {
  const done = status === "completed" || status === "ready" || status === "done";
  const working = status === "analyzing" || status === "uploading" || status === "uploaded";
  return (
    <span
      className={cn(
        "ml-auto h-1.5 w-1.5 shrink-0 rounded-full",
        done ? "bg-emerald-500" : working ? "bg-amber-500" : "bg-muted-foreground/40"
      )}
      aria-hidden
    />
  );
}
