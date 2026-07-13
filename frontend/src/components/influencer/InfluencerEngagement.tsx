"use client";
import { useState, useEffect } from "react";

interface EngagementData {
  total_posts_with_metrics: number;
  totals: {
    likes: number;
    comments: number;
    shares: number;
    saves: number;
    reach: number;
    impressions: number;
  };
  avg_engagement_score: number;
  topic_performance: {
    topic: string;
    weight: number;
    avg_engagement: number;
    avg_reach: number;
    avg_likes: number;
    avg_saves: number;
    total_posts: number;
  }[];
  top_posts: {
    instagram_id: string;
    topic: string;
    likes: number;
    comments: number;
    shares: number;
    saves: number;
    reach: number;
    engagement_score: number;
    published_at: string | null;
  }[];
}

const TOPIC_META: Record<string, { label: string; color: string; emoji: string }> = {
  meme:         { label: "Meme",        color: "#ffd700", emoji: "😂" },
  noticias:     { label: "Noticias",    color: "#60a5fa", emoji: "📰" },
  insight:      { label: "Insight",     color: "#00ff88", emoji: "💡" },
  profits:      { label: "Profits",     color: "#00ff88", emoji: "💰" },
  erros:        { label: "Erros",       color: "#ff4444", emoji: "😅" },
  aprendizados: { label: "Aprendizados", color: "#c084fc", emoji: "📚" },
  market:       { label: "Mercado",     color: "#60a5fa", emoji: "📊" },
  trade:        { label: "Trade",       color: "#00ff88", emoji: "📈" },
  news:         { label: "Noticia",     color: "#c084fc", emoji: "📰" },
};

function formatNum(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toString();
}

export default function InfluencerEngagement() {
  const [data, setData] = useState<EngagementData | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const fetchEngagement = async () => {
    try {
      const resp = await fetch("/api/v1/biel/engagement");
      if (resp.ok) setData(await resp.json());
    } catch (e) {
      console.error("Erro ao carregar engajamento:", e);
    } finally {
      setLoading(false);
    }
  };

  const forceSync = async () => {
    setSyncing(true);
    try {
      await fetch("/api/v1/biel/engagement/sync", { method: "POST" });
      await fetchEngagement();
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => { fetchEngagement(); }, []);

  if (loading) {
    return (
      <div style={{ color: "#3d5a80", fontSize: 12, textAlign: "center", padding: 30 }}>
        Carregando metricas de engajamento...
      </div>
    );
  }

  if (!data || data.total_posts_with_metrics === 0) {
    return (
      <div style={{
        background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12,
        padding: 24, textAlign: "center",
      }}>
        <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 14, marginBottom: 10 }}>
          📊 Engajamento do Instagram
        </div>
        <div style={{ color: "#3d5a80", fontSize: 12, marginBottom: 16 }}>
          Nenhuma metrica coletada ainda. As metricas sao coletadas automaticamente a cada 6 horas
          para posts publicados.
        </div>
        <button onClick={forceSync} disabled={syncing} style={{
          background: syncing ? "#141c2e" : "#1e3a5f",
          color: syncing ? "#3d5a80" : "#60a5fa",
          border: "1px solid #2563eb", borderRadius: 8,
          padding: "8px 20px", fontSize: 12, cursor: syncing ? "default" : "pointer",
        }}>
          {syncing ? "Sincronizando..." : "🔄 Sincronizar Agora"}
        </button>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

      {/* Header + Sync button */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ color: "#ffd700", fontWeight: 700, fontSize: 14 }}>
          📊 Engajamento do Instagram
        </div>
        <button onClick={forceSync} disabled={syncing} style={{
          background: syncing ? "#141c2e" : "#0d1525",
          color: syncing ? "#3d5a80" : "#60a5fa",
          border: "1px solid #2563eb", borderRadius: 8,
          padding: "5px 14px", fontSize: 10, cursor: syncing ? "default" : "pointer",
        }}>
          {syncing ? "..." : "🔄 Sync"}
        </button>
      </div>

      {/* Totals grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
        {[
          { label: "Likes",      value: data.totals.likes,      color: "#ff4444", emoji: "❤️" },
          { label: "Comments",   value: data.totals.comments,   color: "#60a5fa", emoji: "💬" },
          { label: "Shares",     value: data.totals.shares,     color: "#00ff88", emoji: "🔗" },
          { label: "Saves",      value: data.totals.saves,      color: "#ffd700", emoji: "🔖" },
          { label: "Alcance",    value: data.totals.reach,      color: "#c084fc", emoji: "👁️" },
          { label: "Eng. Score", value: Math.round(data.avg_engagement_score), color: "#ff8800", emoji: "⚡" },
        ].map(({ label, value, color, emoji }) => (
          <div key={label} style={{
            background: "#0d1525", border: "1px solid #141c2e", borderRadius: 10,
            padding: "14px 12px", textAlign: "center",
          }}>
            <div style={{ fontSize: 14, marginBottom: 4 }}>{emoji}</div>
            <div style={{ color: "#3d5a80", fontSize: 9, textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
            <div style={{ color, fontSize: 22, fontWeight: 800, marginTop: 4 }}>{formatNum(value)}</div>
          </div>
        ))}
      </div>

      {/* Topic Performance */}
      {data.topic_performance.length > 0 && (
        <div style={{
          background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20,
        }}>
          <div style={{ color: "#c084fc", fontWeight: 700, fontSize: 13, marginBottom: 14 }}>
            🎯 Performance por Topico (Peso Adaptativo)
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {data.topic_performance.map(tp => {
              const meta = TOPIC_META[tp.topic] || { label: tp.topic, color: "#888", emoji: "📌" };
              const weightBar = Math.min(tp.weight / 3.0, 1.0) * 100;
              const weightColor = tp.weight >= 1.0 ? "#00ff88" : tp.weight >= 0.7 ? "#ffd700" : "#ff4444";
              return (
                <div key={tp.topic} style={{
                  background: "#060d1a", borderRadius: 8, padding: "10px 14px",
                  border: `1px solid ${meta.color}22`,
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                      <span style={{ fontSize: 14 }}>{meta.emoji}</span>
                      <span style={{ color: meta.color, fontWeight: 700, fontSize: 12 }}>{meta.label}</span>
                      <span style={{
                        fontSize: 9, padding: "1px 6px", borderRadius: 6,
                        color: weightColor, background: weightColor + "22",
                        border: `1px solid ${weightColor}44`, fontWeight: 700,
                      }}>
                        x{tp.weight.toFixed(2)}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 14, fontSize: 10, color: "#8899aa" }}>
                      <span>{tp.total_posts} posts</span>
                      <span>{formatNum(tp.avg_reach)} alcance</span>
                      <span>{tp.avg_likes.toFixed(0)} likes</span>
                      <span>{tp.avg_saves.toFixed(0)} saves</span>
                    </div>
                  </div>
                  <div style={{ marginTop: 8, background: "#141c2e", borderRadius: 4, height: 3 }}>
                    <div style={{
                      width: `${weightBar}%`, height: "100%",
                      background: weightColor, borderRadius: 4,
                      transition: "width 0.5s",
                    }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Top Posts */}
      {data.top_posts.length > 0 && (
        <div style={{
          background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20,
        }}>
          <div style={{ color: "#ffd700", fontWeight: 700, fontSize: 13, marginBottom: 14 }}>
            🏆 Top Posts por Engajamento
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {data.top_posts.map((post, i) => {
              const meta = TOPIC_META[post.topic] || { label: post.topic, color: "#888", emoji: "📌" };
              return (
                <div key={post.instagram_id + i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  background: "#060d1a", borderRadius: 8, padding: "8px 14px",
                  border: `1px solid ${i === 0 ? "#ffd70044" : "#141c2e"}`,
                }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <span style={{ color: i === 0 ? "#ffd700" : "#3d5a80", fontWeight: 800, fontSize: 14, width: 20 }}>
                      #{i + 1}
                    </span>
                    <span>{meta.emoji}</span>
                    <span style={{ color: meta.color, fontSize: 12, fontWeight: 600 }}>{meta.label}</span>
                    {post.published_at && (
                      <span style={{ color: "#3d5a80", fontSize: 9 }}>
                        {new Date(post.published_at).toLocaleDateString("pt-BR")}
                      </span>
                    )}
                  </div>
                  <div style={{ display: "flex", gap: 12, fontSize: 10, color: "#8899aa" }}>
                    <span>❤️ {post.likes}</span>
                    <span>💬 {post.comments}</span>
                    <span>🔗 {post.shares}</span>
                    <span>🔖 {post.saves}</span>
                    <span style={{ color: "#ff8800", fontWeight: 700 }}>
                      ⚡ {post.engagement_score.toFixed(1)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
