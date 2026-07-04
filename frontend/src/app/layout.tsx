/**
 * TradeAI - Layout Raiz (Fase 12.5 — UX & Navigation Layer)
 */

import type { Metadata } from "next";
import "./globals.css";
import AppShell from "@/components/layout/AppShell";

export const metadata: Metadata = {
  title: {
    default: "TradeAI — Plataforma de Trading Quantitativo",
    template: "%s | TradeAI",
  },
  description: "Plataforma de trading algorítmico quantitativo.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        className="min-h-screen antialiased"
        style={{ background: "#080c14", color: "#f9fafb" }}
      >
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
