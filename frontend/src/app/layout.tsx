import type { Metadata } from "next";
import { Onest, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const onest = Onest({
  variable: "--font-sans",
  subsets: ["latin", "cyrillic"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-mono",
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
    <html lang="ru" className={`${onest.variable} ${jetbrainsMono.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">{children}</body>
    </html>
  );
}
