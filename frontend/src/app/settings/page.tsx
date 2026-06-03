"use client";

import { AppLayout } from "@/components/layout/app-layout";
import { useTheme } from "@/contexts/theme-context";
import { cn } from "@/lib/utils";
import { Moon, Sun } from "lucide-react";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  return (
    <AppLayout breadcrumb={[{ label: "Настройки" }]}>
      <div className="mx-auto max-w-lg space-y-8">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Настройки</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Параметры интерфейса на этом устройстве
          </p>
        </div>

        <section className="rounded-xl border border-border p-5">
          <h2 className="text-sm font-medium text-foreground">Оформление</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Светлая или тёмная тема. Выбор сохраняется в браузере.
          </p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setTheme("light")}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border px-4 py-4 text-sm transition-colors",
                theme === "light"
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              <Sun className="h-5 w-5" />
              Светлая
            </button>
            <button
              type="button"
              onClick={() => setTheme("dark")}
              className={cn(
                "flex flex-col items-center gap-2 rounded-lg border px-4 py-4 text-sm transition-colors",
                theme === "dark"
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border hover:bg-muted"
              )}
            >
              <Moon className="h-5 w-5" />
              Тёмная
            </button>
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
