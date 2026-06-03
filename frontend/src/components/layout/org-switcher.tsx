"use client";

import { useEffect, useState } from "react";
import { Building2, ChevronDown } from "lucide-react";
import { api, type OrganizationAPI } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import { cn } from "@/lib/utils";

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

  if (!isSuperAdmin || !active) {
    if (!active) return null;
    return (
      <div className="mb-2 flex items-center gap-2 rounded-lg bg-sidebar-accent/60 px-2.5 py-1.5 text-xs text-muted-foreground">
        <Building2 className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">{active.name}</span>
      </div>
    );
  }

  return (
    <div className="relative mb-2">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 rounded-lg border border-border/60 bg-background px-2.5 py-1.5 text-left text-xs transition-colors hover:bg-sidebar-accent"
      >
        <Building2 className="h-3.5 w-3.5 shrink-0 text-primary" />
        <span className="min-w-0 flex-1 truncate font-medium text-foreground">
          {active.name}
        </span>
        <ChevronDown className={cn("h-3.5 w-3.5 shrink-0 opacity-60", open && "rotate-180")} />
      </button>
      {open && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1 max-h-48 overflow-y-auto rounded-lg border border-border bg-card py-1 shadow-md">
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
