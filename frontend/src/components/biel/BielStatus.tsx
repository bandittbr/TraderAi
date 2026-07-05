"use client";
import { useEffect, useState } from "react";

interface BielStatusData {
  configured: boolean;
  active: boolean;
  post_hours: string | null;
  posts_per_day: number;
  instagram_account_id: string | null;
  token_active: boolean;
  token_expires_at: string | null;
  recent_posts: {
    id: number;
    topic: string;
    status: string;
    instagram_id: string | null;
    caption_preview: string | null;
    published_at: string | null;
    created_at: string | null;
    error: string | null;
  }[];
}

export default function BielStatus() {
  const [data, setData] = useState<BielStatusData | null>(null);
  const [posting, setPosting] = useState(false);
  const [postMsg, setPostMsg] = useState("");

  const fetch_ = () =>
    fetch("/api/v1/biel/status")
      .then(r => r.json())
      .then(setData)
      .catch(() => {});

  useEffect(() => {
    fetch_();
    const t = setInterval(fetch_, 30000);
    return () => clearInterval(t);
  }, []);

  const forcePost = async (topic?: string) => {
    setPosting(true);
    setPostMsg("");
    try {
      const r = await fetch("/api/v1/biel/post", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic || null }),
      });
      const j = await r.json();
      if (j.status === "published") {
        setPostMsg(`✅ Publicado! IG: ${j.instagram_id}`);
      } else {
        setPostMsg(`❌ ${j.detail || j.error}`);
      }
      fetch_();
    } catch (e) {
      setPostMsg("❌ Erro de conexão");
    }
    setPosting(false);
  };

  const statusColor = (s: string) => ({
    published: "#00ff88",
    failed:    "#ff4444",
    pending:   "#ffd700",
  }[s] || "#888");

  const topicLabel = (t: string) => ({
    market:  "📊 Mercado",
    trade:   "📈 Trade",
    insight: "💡 Insight",
    news:    "📰 Notícia",
  }[t] || t);

  if (!data) return (
    <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20 }}>
      <div style={{ color: "#3d5a80", fontSize: 12 }}>Carregando Biel...</div>
    </div>
  );

  return (
    <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ color: "#ffd700", fontWeight: 700, fontSize: 16 }}>⚡ Biel Agent</div>
          <div style={{ color: "#3d5a80", fontSize: 11, marginTop: 2 }}>Instagram Autônomo · Gemini 2.0 Flash</div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <div style={{
            fontSize: 10, padding: "3px 10px", borderRadius: 20, fontWeight: 700,
            background: data.configured && data.token_active ? "#0a2a1a" : "#2a0a0a",
            color: data.configured && data.token_active ? "#00ff88" : "#ff4444",
            border: `1px solid ${data.configured && data.token_active ? "#00ff4422" : "#ff444422"}`,
          }}>
            {data.configured && data.token_active ? "ATIVO" : "INATIVO"}
          </div>
        </div>
      </div>

      {/* Config info */}
      {data.configured && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
          {[
            { label: "Posts/dia", value: String(data.posts_per_day) },
            { label: "Horários", value: data.post_hours || "—" },
            { label: "Token IG", value: data.token_active ? "Ativo" : "Inativo" },
          ].map(({ label, value }) => (
            <div key={label} style={{ background: "#060d1a", borderRadius: 8, padding: "8px 10px" }}>
              <div style={{ color: "#3d5a80", fontSize: 9 }}>{label}</div>
              <div style={{ color: "#60a5fa", fontSize: 13, fontWeight: 700, marginTop: 2 }}>{value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Token expiry */}
      {data.token_expires_at && (
        <div style={{ fontSize: 10, color: "#3d5a80" }}>
          Token expira: <span style={{ color: "#ffd700" }}>
            {new Date(data.token_expires_at).toLocaleDateString("pt-BR")}
          </span>
        </div>
      )}

      {/* Force post buttons */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {["market", "trade", "insight", "news"].map(t => (
          <button key={t}
            onClick={() => forcePost(t)}
            disabled={posting}
            style={{
              fontSize: 11, padding: "5px 12px", borderRadius: 8, cursor: posting ? "not-allowed" : "pointer",
              background: "#1e3a5f", color: "#60a5fa", border: "1px solid #2563eb",
              opacity: posting ? 0.5 : 1, transition: "opacity 0.2s",
            }}>
            {posting ? "..." : topicLabel(t)}
          </button>
        ))}
      </div>
      {postMsg && <div style={{ fontSize: 11, color: postMsg.startsWith("✅") ? "#00ff88" : "#ff4444" }}>{postMsg}</div>}

      {/* Recent posts */}
      {data.recent_posts.length > 0 && (
        <div>
          <div style={{ color: "#3d5a80", fontSize: 10, marginBottom: 6 }}>POSTS RECENTES</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {data.recent_posts.slice(0, 5).map(p => (
              <div key={p.id} style={{
                background: "#060d1a", borderRadius: 8, padding: "8px 10px",
                border: `1px solid ${statusColor(p.status)}22`,
                display: "flex", flexDirection: "column", gap: 3,
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "#60a5fa", fontSize: 11 }}>{topicLabel(p.topic || "")}</span>
                  <span style={{ color: statusColor(p.status), fontSize: 10, fontWeight: 700 }}>
                    {p.status.toUpperCase()}
                  </span>
                </div>
                {p.caption_preview && (
                  <div style={{ color: "#8899aa", fontSize: 10, lineHeight: 1.4 }}>{p.caption_preview}</div>
                )}
                {p.error && (
                  <div style={{ color: "#ff4444", fontSize: 10 }}>Erro: {p.error.slice(0, 80)}</div>
                )}
                <div style={{ color: "#3d5a80", fontSize: 9 }}>
                  {p.published_at ? new Date(p.published_at).toLocaleString("pt-BR") : "—"}
                  {p.instagram_id && <span style={{ color: "#00ff8888", marginLeft: 8 }}>IG: {p.instagram_id}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!data.configured && (
        <div style={{ background: "#1a0a00", border: "1px solid #ff660033", borderRadius: 8, padding: 12 }}>
          <div style={{ color: "#ffd700", fontSize: 12, fontWeight: 700 }}>⚠ Configuração necessária</div>
          <div style={{ color: "#8899aa", fontSize: 11, marginTop: 4 }}>
            Use o painel de Setup abaixo para configurar a API do Gemini e o token do Instagram.
          </div>
        </div>
      )}
    </div>
  );
}
