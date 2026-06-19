"use client";

import {
  createContext,
  Suspense,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthModal, type AuthModalMode } from "@/components/landing/auth-modal";

type LandingAuthContextValue = {
  openLogin: (next?: string) => void;
  openRegister: (next?: string) => void;
};

const LandingAuthContext = createContext<LandingAuthContextValue | null>(null);

export function useLandingAuth() {
  const ctx = useContext(LandingAuthContext);
  if (!ctx) {
    throw new Error("useLandingAuth must be used within LandingLoginHost");
  }
  return ctx;
}

/** @deprecated use useLandingAuth */
export const useLandingLogin = useLandingAuth;

function cleanAuthParams(params: URLSearchParams) {
  params.delete("login");
  params.delete("register");
  params.delete("next");
}

function AuthUrlSync({
  onSync,
}: {
  onSync: (payload: { mode: AuthModalMode; next: string }) => void;
}) {
  const searchParams = useSearchParams();

  useEffect(() => {
    const wantsLogin = searchParams.get("login") === "1";
    const wantsRegister = searchParams.get("register") === "1";
    if (wantsLogin || wantsRegister) {
      onSync({
        mode: wantsRegister ? "register" : "login",
        next: searchParams.get("next") || "/",
      });
    }
  }, [searchParams, onSync]);

  return null;
}

export function LandingLoginHost({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<AuthModalMode>("login");
  const [next, setNext] = useState("/");

  const openLogin = useCallback((nextPath = "/") => {
    setMode("login");
    setNext(nextPath);
    setOpen(true);
  }, []);

  const openRegister = useCallback((nextPath = "/") => {
    setMode("register");
    setNext(nextPath);
    setOpen(true);
  }, []);

  const handleUrlSync = useCallback(
    (payload: { mode: AuthModalMode; next: string }) => {
      setMode(payload.mode);
      setNext(payload.next);
      setOpen(true);
    },
    []
  );

  const handleOpenChange = useCallback(
    (isOpen: boolean) => {
      setOpen(isOpen);
      if (!isOpen && typeof window !== "undefined") {
        const params = new URLSearchParams(window.location.search);
        if (params.get("login") || params.get("register")) {
          cleanAuthParams(params);
          const qs = params.toString();
          router.replace(`/landing${qs ? `?${qs}` : ""}`, { scroll: false });
        }
      }
    },
    [router]
  );

  const value = useMemo(() => ({ openLogin, openRegister }), [openLogin, openRegister]);

  return (
    <LandingAuthContext.Provider value={value}>
      {children}
      <Suspense fallback={null}>
        <AuthUrlSync onSync={handleUrlSync} />
      </Suspense>
      <AuthModal
        open={open}
        onOpenChange={handleOpenChange}
        mode={mode}
        onModeChange={setMode}
        next={next}
      />
    </LandingAuthContext.Provider>
  );
}
