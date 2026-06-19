"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { api, type AuthConfigAPI, type UserAPI } from "@/lib/api";

type AuthContextValue = {
  user: UserAPI | null;
  config: AuthConfigAPI | null;
  loading: boolean;
  refresh: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string,
    password: string,
    displayName: string,
    registrationCode: string
  ) => Promise<void>;
  switchOrganization: (organizationId: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const PUBLIC_PATHS = ["/landing", "/login", "/register", "/help"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<UserAPI | null>(null);
  const [config, setConfig] = useState<AuthConfigAPI | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const [cfg, me] = await Promise.all([api.auth.config(), api.auth.me()]);
    setConfig(cfg);
    setUser(me);
  }, []);

  useEffect(() => {
    let active = true;
    void refresh()
      .catch(() => {
        if (active) {
          setConfig({ auth_required: false, authenticated: false });
          setUser(null);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [refresh]);

  useEffect(() => {
    if (loading || !config?.auth_required) return;
    if (user) return;
    const isPublic =
      PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`));
    if (!isPublic) {
      router.replace(`/landing?login=1&next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, config, user, pathname, router]);

  const login = useCallback(
    async (email: string, password: string) => {
      const u = await api.auth.login({ email, password });
      setUser(u);
      setConfig((c) => (c ? { ...c, authenticated: true } : c));
    },
    []
  );

  const register = useCallback(
    async (
      email: string,
      password: string,
      displayName: string,
      registrationCode: string
    ) => {
      const u = await api.auth.register({
        email,
        password,
        display_name: displayName,
        registration_code: registrationCode,
      });
      setUser(u);
      setConfig((c) => (c ? { ...c, authenticated: true } : c));
    },
    []
  );

  const switchOrganization = useCallback(async (organizationId: string) => {
    const u = await api.auth.switchOrganization(organizationId);
    setUser(u);
  }, []);

  const logout = useCallback(async () => {
    await api.auth.logout();
    setUser(null);
    setConfig((c) => (c ? { ...c, authenticated: false } : c));
    router.push("/landing");
  }, [router]);

  const value = useMemo(
    () => ({
      user,
      config,
      loading,
      refresh,
      login,
      register,
      logout,
      switchOrganization,
    }),
    [user, config, loading, refresh, login, register, logout, switchOrganization]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
