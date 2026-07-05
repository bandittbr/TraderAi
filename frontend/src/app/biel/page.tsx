"use client";
import { useState } from "react";
import BielStatus from "@/components/biel/BielStatus";
import BielSetup  from "@/components/biel/BielSetup";
import BielPosts  from "@/components/biel/BielPosts";

export default function BielPage() {
  const [tab, setTab] = useState<"status" | "setup" | "posts">("status");

  const tabs = [
    { key: "status", label: "⚡ Status" },
    { key: "setup",  label: "🔧 Setup" },
    { key: "posts",  label: "📋 Posts" },
  ] as const;

  return (
    <div className="p-6 space-y-5 max-w-[1200px] mx-auto">

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ color: "#ffd700", fontWeight: 700, fontSize: 20 }}>⚡ Biel — Instagram Agent</h1>
          <p style={{ color: "#3d5a80", fontSize: 11, marginTop: 4 }}>
            Inteligência artificial autônoma · Gemini 2.0 Flash · Instagram Graph API · 4 posts/dia
          </p>
        </div>
        <div style={{
          fontSize: 10, padding: "4px 12px", borderRadius: 20,
          background: "#1a1a00", color: "#ffd700", border: "1px solid #ffd70033",
          fontWeight: 700,
        }}>
          BETA
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 6 }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{
              fontSize: 12, padding: "6px 16px", borderRadius: 8, cursor: "pointer",
              background: tab === t.key ? "#1e3a5f" : "#0d1525",
              color:      tab === t.key ? "#60a5fa" : "#3d5a80",
              border:     `1px solid ${tab === t.key ? "#2563eb" : "#141c2e"}`,
              transition: "all 0.2s",
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      {tab === "status" && <BielStatus />}
      {tab === "setup"  && <BielSetup onSetupDone={() => setTab("status")} />}
      {tab === "posts"  && <BielPosts />}

      {/* Info box */}
      <div style={{
        background: "#060d1a", border: "1px solid #141c2e", borderRadius: 12,
        padding: 16, fontSize: 11, color: "#3d5a80", lineHeight: 1.7,
      }}>
        <div style={{ color: "#60a5fa", fontWeight: 700, marginBottom: 6 }}>Como funciona</div>
        <div>
          1. <b style={{ color: "#c8d8e8" }}>Setup:</b> Configure a Gemini API Key e o token do Instagram Business.<br />
          2. <b style={{ color: "#c8d8e8" }}>Automático:</b> O Biel posta 4x/dia nos horários configurados (padrão 8h, 12h, 18h, 22h UTC).<br />
          3. <b style={{ color: "#c8d8e8" }}>Tópicos:</b> Rotaciona entre Mercado → Trade → Insight → Notícia.<br />
          4. <b style={{ color: "#c8d8e8" }}>Token:</b> Renovação automática quando faltar 7 dias para expirar (60 dias).<br />
          5. <b style={{ color: "#c8d8e8" }}>Dados reais:</b> Usa P&amp;L, Win Rate, BTC price, Regime, Fear&amp;Greed e Notícias do TradeAI.
        </div>
      </div>
    </div>
  );
}
