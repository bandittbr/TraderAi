"use client";
import { useState } from "react";

interface Post {
  id: number;
  post_type: string;
  topic: string | null;
  reel_topic: string | null;
  status: string;
  instagram_id: string | null;
  caption: string | null;
  video_path: string | null;
  image_path: string | null;
  regime: string | null;
  pnl_snapshot: number | null;
  error: string | null;
  published_at: string | null;
  created_at: string | null;
}

const REEL_TOPIC_META: Record<string, { label: string; color: string; emoji: string }> = {
  meme:         { label: "Meme",        color: "#ffd700", emoji: "😂" },
  noticias:     { label: "Notícias",    color: "#60a5fa", emoji: "📰" },
  insight:      { label: "Insight",     color: "#00ff88", emoji: "💡" },
  profits:      { label: "Profits",     color: "#00ff88", emoji: "💰" },
  erros:        { label: "Erros",       color: "#ff4444", emoji: "😅" },
  aprendizados: { label: "Aprendizados", color: "#c084fc", emoji: "📚" },
};

function statusBadge(s: string) {
  const map: Record<string, [string, string]> = {
    published: ["#00ff88", "PUBLICADO"],
    failed:    ["#ff4444", "FALHOU"],
    pending:   ["#ffd700", "PENDENTE"],
  };
  const [color, label] = map[s] || ["#888", s.toUpperCase()];
  return (
    <span style={{
      fontSize: 9, padding: "2px 8px", borderRadius: 10, fontWeight: 800,
      background: color + "22", color, border: `1px solid ${color}44`,
    }}>
      {label}
    </span>
  );
}

function timeAgo(iso: string | null) {
  if (!iso) return "—";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s atrás`;
  if (diff < 3600) return `${Math.floor(diff / 60)}min atrás`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h atrás`;
  return `${Math.floor(diff / 86400)}d atrás`;
}

export default function InfluencerReelsFeed({ posts }: { posts: Post[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);
  const [filter, setFilter] = useState<string>("all");

  const reels = posts.filter(p => p.post_type === "reel");
  const filtered = filter === "all" ? reels : reels.filter(p => p.reel_topic === filter || p.status === filter);

  return (
    <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div style={{ color: "#c084fc", fontWeight: 700, fontSize: 14 }}>
          🎬 Reels Publicados ({reels.length})
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {["all", "meme", "noticias", "insight", "profits", "erros", "aprendizados", "failed"].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              style={{
                fontSize: 10, padding: "3px 10px", borderRadius: 8, cursor: "pointer",
                background: filter === f ? "#2a1a4a" : "#060d1a",
                color: filter === f ? "#c084fc" : "#3d5a80",
                border: `1px solid ${filter === f ? "#8b5cf6" : "#141c2e"}`,
              }}>
              {f === "all" ? "Todos" : f === "failed" ? "❌ Erros" : (REEL_TOPIC_META[f]?.emoji + " " + REEL_TOPIC_META[f]?.label)}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 && (
        <div style={{ color: "#3d5a80", fontSize: 12, textAlign: "center", padding: 30 }}>
          Nenhum reel encontrado.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 600, overflowY: "auto" }}>
        {filtered.map(p => {
          const meta = REEL_TOPIC_META[p.reel_topic || ""] || { label: p.reel_topic || "reel", color: "#888", emoji: "🎬" };
          const isOpen = expanded === p.id;
          return (
            <div key={p.id}
              onClick={() => setExpanded(isOpen ? null : p.id)}
              style={{
                background: "#060d1a",
                border: `1px solid ${isOpen ? meta.color + "44" : "#141c2e"}`,
                borderRadius: 10,
                padding: "12px 14px",
                cursor: "pointer",
                transition: "border-color 0.2s",
              }}>
              {/* Row compacta */}
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: 18, flexShrink: 0 }}>{meta.emoji}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                    <span style={{ color: meta.color, fontWeight: 700, fontSize: 12 }}>{meta.label}</span>
                    {statusBadge(p.status)}
                  </div>
                  {p.caption && (
                    <div style={{
                      color: "#8899aa", fontSize: 11, marginTop: 4,
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: isOpen ? "normal" : "nowrap",
                    }}>
                      {p.caption}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: "right", flexShrink: 0 }}>
                  <div style={{ color: "#3d5a80", fontSize: 10 }}>
                    {timeAgo(p.published_at || p.created_at)}
                  </div>
                  {p.published_at && (
                    <div style={{ color: "#1e3a5f", fontSize: 9, marginTop: 2 }}>
                      {new Date(p.published_at).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}
                    </div>
                  )}
                </div>
              </div>

              {/* Expanded */}
              {isOpen && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid #141c2e", display: "flex", flexDirection: "column", gap: 8 }}>
                  {p.caption && (
                    <div style={{
                      background: "#0a1525", borderRadius: 8, padding: "10px 12px",
                      color: "#c8d8e8", fontSize: 12, lineHeight: 1.6, whiteSpace: "pre-wrap",
                    }}>
                      {p.caption}
                    </div>
                  )}
                  <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                    {p.instagram_id && (
                      <div style={{ fontSize: 10, color: "#3d5a80" }}>
                        🔗 Instagram ID: <span style={{ color: "#60a5fa", fontFamily: "monospace" }}>{p.instagram_id}</span>
                      </div>
                    )}
                    {p.video_path && (
                      <div style={{ fontSize: 10, color: "#3d5a80" }}>
                        🎬 Reel: <span style={{ color: "#888", fontFamily: "monospace", fontSize: 9 }}>{p.video_path.split("/").pop()}</span>
                      </div>
                    )}
                  </div>
                  {p.error && (
                    <div style={{ background: "#2a0a0a", borderRadius: 6, padding: "6px 10px", color: "#ff4444", fontSize: 11 }}>
                      ⚠ {p.error}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
