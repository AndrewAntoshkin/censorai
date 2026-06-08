"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { ChevronsUpDown } from "lucide-react";
import { api, type OrganizationAPI } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";

/** Inline org switcher for super admin — sits in the sidebar header next to the logo icon. */
export function OrgSwitcher() {
  const { user, switchOrganization } = useAuth();
  const [orgs, setOrgs] = useState<OrganizationAPI[]>([]);
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);

  const isSuperAdmin = user?.role === "super_admin";
  const active = user?.active_organization ?? user?.organization;

  useEffect(() => {
    if (!isSuperAdmin) return;
    void api.auth
      .listOrganizations()
      .then(setOrgs)
      .catch(() => setOrgs([]));
  }, [isSuperAdmin]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    const onClick = () => setOpen(false);
    window.addEventListener("keydown", onKey);
    window.addEventListener("click", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("click", onClick);
    };
  }, [open]);

  if (!isSuperAdmin || !active) {
    return null;
  }

  return (
    <div className="relative min-w-0 flex-1">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
        className="group flex w-full min-w-0 items-center gap-2 rounded-lg px-1.5 py-1.5 text-left transition-colors hover:bg-sidebar-accent"
      >
        <span className="relative h-5 w-5 shrink-0 overflow-hidden rounded-sm">
          <Image
            src="/logo.png"
            alt=""
            width={98}
            height={20}
            priority
            className="h-5 w-auto max-w-none"
          />
        </span>
        <span className="min-w-0 truncate text-sm font-medium text-foreground">
          {active.name}
        </span>
        <ChevronsUpDown className="ml-auto h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-60 transition-opacity group-hover:opacity-100" />
      </button>
      {open && (
        <div
          className="absolute left-0 right-0 top-full z-50 mt-1 max-h-48 overflow-y-auto rounded-lg border border-border bg-card py-1 shadow-md"
          onClick={(e) => e.stopPropagation()}
        >
          {orgs.map((org) => (
            <button
              key={org.id}
              type="button"
              disabled={pending}
              onClick={() => {
                setPending(true);
                void switchOrganization(org.id)
                  .then(() => {
                    setOpen(false);
                    window.location.reload();
                  })
                  .finally(() => setPending(false));
              }}
              className={cn(
                "flex w-full px-2.5 py-1.5 text-left text-xs hover:bg-sidebar-accent",
                org.id === active.id && "bg-primary/10 font-medium text-primary"
              )}
            >
              {org.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
