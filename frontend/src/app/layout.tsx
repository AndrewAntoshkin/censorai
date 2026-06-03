import type { Metadata } from "next";
import Script from "next/script";
import { Onest } from "next/font/google";
import "./globals.css";
import { UploadUnloadGuard } from "@/components/upload/upload-unload-guard";
import { AuthProvider } from "@/contexts/auth-context";
import { WorkspaceProvider } from "@/contexts/workspace-context";
import { ThemeProvider } from "@/contexts/theme-context";

const onest = Onest({
  variable: "--font-sans",
  subsets: ["latin", "cyrillic"],
});

export const metadata: Metadata = {
  title: "фреймчек — Анализ видеоконтента",
  description: "Сервис анализа видеоконтента на соответствие требованиям законодательства РФ",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru" className={`${onest.variable} h-full antialiased`} suppressHydrationWarning>
      <body className="min-h-full font-sans">
        <Script
          id="fc-theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("fc-theme");if(t==="dark")document.documentElement.classList.add("dark");}catch(e){}})();`,
          }}
        />
        <ThemeProvider>
          <AuthProvider>
            <WorkspaceProvider>
              <UploadUnloadGuard />
              {children}
            </WorkspaceProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
