"use client";

import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  breadcrumb: { label: string; href?: string }[];
  onUpload?: () => void;
}

export function Header({ breadcrumb, onUpload }: HeaderProps) {
  return (
    <header className="flex h-13 shrink-0 items-center justify-between border-b border-border px-5 py-2">
      <nav className="flex min-w-0 items-center gap-1.5 text-sm">
        {breadcrumb.map((item, i) => (
          <span key={i} className="flex min-w-0 items-center gap-1.5">
            {i > 0 && <span className="text-border">/</span>}
            {item.href ? (
              <a
                href={item.href}
                className="truncate text-muted-foreground transition-colors hover:text-foreground"
              >
                {item.label}
              </a>
            ) : (
              <span className="truncate font-medium text-foreground">
                {item.label}
              </span>
            )}
          </span>
        ))}
      </nav>

      {onUpload && (
        <Button onClick={onUpload} size="lg" className="gap-1.5">
          <Plus className="h-4 w-4" />
          Загрузить
        </Button>
      )}
    </header>
  );
}
