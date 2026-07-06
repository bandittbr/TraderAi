"use client";
import { useState } from "react";

interface ControlsProps {
  status: {
    configured: boolean;
    active: boolean;
    token_active: boolean;
    token_expires_at: string | null;
    token_days_left: number | null;
    post_hours: string | null;
    posts_per_day: number;
    instagram_account_id: string | null;
  };
  onRefresh: () => void;
}

const TOPICS = [
  { key: "market",  label: "📊 Mercado",  color: "#2563eb" },
  { key: "trade",   label: "📈 Trade",    color: "#059669" },
  { key: "insight", label: "💡 Insight",  color: "#d97706" },
  { key: "news",    label: "📰 Notícia",  color: "#7c3aed" },
];

export default function InfluencerControls({ status, onRefresh }: ControlsProps) {
  const [posting, setPosting] = useState<string | null>(null);
  const [msg, setMsg] = useState("");
  const [renewing, setRenewing] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState<any>(null);
  const [newToken, setNewToken] = useState("");
  const [updatingToken, setUpdatingToken] = useState(false);
  const [tokenMsg, setTokenMsg] = useState("");

  const forcePost = async (topic: string) => {
    setPosting(topic);
    setMsg("");
    try {
      const r = await fetch("/api/v1/biel/post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic }),
      });
      const j = await r.json();
      if (j.status === "published") {
        setMsg(`✅ Post "${topic}" publicado! IG: ${j.instagram_id}`);
        onRefresh();
      } else {
        setMsg(`❌ Erro: ${j.detail || j.error}`);
      }
    } catch {
      setMsg("❌ Erro de conexão com o backend");
    }
    setPosting(null);
  };

  const renewToken = async () => {
    setRenewing(true);
    setMsg("");
    try {
      const r = await fetch("/api/v1/biel/token/renew", { method: "POST" });
      const j = await r.json();
      setMsg(`✅ Token renovado! Expira: ${j.expires_at ? new Date(j.expires_at).toLocaleDateString("pt-BR") : "—"}`);
      onRefresh();
    } catch {
      setMsg("❌ Erro ao renovar token");
    }
    setRenewing(false);
  };

  const verifyToken = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const r = await fetch("/api/v1/biel/token/verify");
      const j = await r.json();
      setVerifyResult(j);
    } catch {
      setVerifyResult({ valid: false, error: "Erro de conexão" });
    }
    setVerifying(false);
  };

  const updateToken = async () => {
    if (!newToken.trim()) { setTokenMsg("❌ Cole o novo token"); return; }
    setUpdatingToken(true);
    setTokenMsg("");
    try {
      const r = await fetch("/api/v1/biel/token/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ access_token: newToken.trim() }),
      });
      const j = await r.json();
      if (r.ok) {
        setTokenMsg(`✅ Token atualizado! Prefixo: ${j.token_prefix}`);
        setNewToken("");
        onRefresh();
      } else {
        setTokenMsg(`❌ ${j.detail || "Erro desconhecido"}`);
      }
    } catch {
      setTokenMsg("❌ Erro de conexão");
    }
    setUpdatingToken(false);
  };

  const tokenDays = status.token_days_left;
  const tokenColor = tokenDays === null ? "#888" : tokenDays <= 7 ? "#ff4444" : tokenDays <= 14 ? "#ffd700" : "#00ff88";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

      {/* Forçar post */}
      <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20 }}>
        <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 14, marginBottom: 14 }}>
          🚀 Forçar Post Manual
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {TOPICS.map(t => (
            <button key={t.key}
              onClick={() => forcePost(t.key)}
              disabled={posting !== null}
              style={{
                background: posting === t.key ? t.color + "55" : t.color + "22",
                border: `1px solid ${t.color}44`,
                borderRadius: 10, padding: "12px 10px",
                color: "#c8d8e8", fontSize: 13, fontWeight: 700,
                cursor: posting !== null ? "not-allowed" : "pointer",
                opacity: posting !== null && posting !== t.key ? 0.5 : 1,
                transition: "all 0.2s",
              }}>
              {posting === t.key ? "Publicando..." : t.label}
            </button>
          ))}
        </div>
        {msg && (
          <div style={{
            marginTop: 10, fontSize: 11, padding: "8px 12px", borderRadius: 8,
            background: msg.startsWith("✅") ? "#0a2a1a" : "#2a0a0a",
            color: msg.startsWith("✅") ? "#00ff88" : "#ff4444",
            border: `1px solid ${msg.startsWith("✅") ? "#00ff4422" : "#ff444422"}`,
          }}>
            {msg}
          </div>
        )}
      </div>

      {/* Configuração atual */}
      <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20 }}>
        <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 14, marginBottom: 14 }}>
          ⚙️ Configuração Atual
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[
            { label: "Status",          value: status.configured && status.active ? "Ativo" : "Inativo", color: status.configured && status.active ? "#00ff88" : "#ff4444" },
            { label: "Posts por dia",   value: String(status.posts_per_day),  color: "#60a5fa" },
            { label: "Horários (UTC)",  value: status.post_hours || "—",      color: "#ffd700" },
            { label: "Conta IG",        value: status.instagram_account_id ? status.instagram_account_id.slice(0, 12) + "…" : "Não configurada", color: "#c084fc" },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ color: "#3d5a80", fontSize: 12 }}>{label}</span>
              <span style={{ color, fontSize: 12, fontWeight: 700 }}>{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Token Instagram */}
      <div style={{
        background: "#0d1525",
        border: `1px solid ${tokenColor}44`,
        borderRadius: 12, padding: 20,
      }}>
        <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 14, marginBottom: 14 }}>
          🔑 Token Instagram
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div>
            <div style={{ color: tokenColor, fontSize: 22, fontWeight: 800 }}>
              {tokenDays !== null ? `${tokenDays} dias` : "—"}
            </div>
            <div style={{ color: "#3d5a80", fontSize: 11, marginTop: 2 }}>
              {status.token_expires_at
                ? `Expira em ${new Date(status.token_expires_at).toLocaleDateString("pt-BR")}`
                : "Sem data de expiração"}
            </div>
          </div>
          <button onClick={renewToken} disabled={renewing}
            style={{
              background: "#1e3a5f", color: "#60a5fa", border: "1px solid #2563eb",
              borderRadius: 8, padding: "8px 14px", fontSize: 12, fontWeight: 700,
              cursor: renewing ? "not-allowed" : "pointer", opacity: renewing ? 0.6 : 1,
            }}>
            {renewing ? "Renovando..." : "Renovar Agora"}
          </button>
        </div>
        {tokenDays !== null && tokenDays <= 7 && (
          <div style={{ background: "#2a0a0a", border: "1px solid #ff444433", borderRadius: 8, padding: "8px 12px" }}>
            <div style={{ color: "#ff4444", fontSize: 11, fontWeight: 700 }}>
              ⚠ Token expira em {tokenDays} dias — renovação automática ativa
            </div>
          </div>
        )}
        <div style={{ color: "#3d5a80", fontSize: 10, marginTop: 10 }}>
          O Biel renova automaticamente quando faltam 7 dias. Você pode forçar a renovação a qualquer momento.
        </div>
      </div>
    </div>
  );
}
