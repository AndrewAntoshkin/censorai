import type { Metadata } from "next";
import { Onest } from "next/font/google";
import "./globals.css";
import { UploadUnloadGuard } from "@/components/upload/upload-unload-guard";
import { AuthProvider } from "@/contexts/auth-context";
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
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("fc-theme");if(t==="dark")document.documentElement.classList.add("dark");}catch(e){}})();`,
          }}
        />
      </head>
      <body className="min-h-full font-sans">
        <ThemeProvider>
          <AuthProvider>
            <UploadUnloadGuard />
            {children}
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
