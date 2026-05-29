"use client";

import { AppLayout } from "@/components/layout/app-layout";
import { Search, Folder, Plus, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api, type ProjectAPI } from "@/lib/api";
import Link from "next/link";
import { useEffect, useState } from "react";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectAPI[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api.projects
      .list()
      .then((p) => active && setProjects(p))
      .catch(() => {})
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  return (
    <AppLayout breadcrumb={[{ label: "Главная", href: "/" }, { label: "Проекты" }]}>
      <div className="mx-auto max-w-5xl space-y-8">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h1 className="mb-1 text-2xl font-semibold tracking-tight text-foreground">
              Проекты
            </h1>
            <p className="text-sm text-muted-foreground">
              {projects.length} проектов
            </p>
          </div>
          <Button variant="outline" size="lg" className="gap-1.5">
            <Plus className="h-4 w-4" />
            Новый проект
          </Button>
        </div>

        <div className="relative">
          <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Поиск проектов"
            className="h-11 rounded-xl pl-10 text-sm"
          />
        </div>

        {loading ? (
          <div className="flex h-40 items-center justify-center gap-3 text-sm text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
            Загрузка…
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            {projects.map((project) => (
              <Link
                key={project.id}
                href={`/project/${project.id}`}
                className="group flex flex-col gap-3 rounded-xl border border-border bg-card p-4 transition-all hover:border-primary/30 hover:shadow-sm"
              >
                <div className="flex aspect-[5/3] w-full items-center justify-center rounded-lg bg-primary/[0.06]">
                  <Folder className="h-9 w-9 text-primary/70" />
                </div>
                <div className="min-w-0">
                  <span className="block truncate text-sm font-medium text-foreground group-hover:text-primary">
                    {project.name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {project.files_count ?? 0} файлов
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
