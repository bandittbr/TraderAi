"use client";
import { useEffect, useState } from "react";

interface Post {
  id: number;
  topic: string;
  status: string;
  instagram_id: string | null;
  caption: string | null;
  image_path: string | null;
  regime: string | null;
  pnl_snapshot: number | null;
  error: string | null;
  published_at: string | null;
  created_at: string | null;
}

interface Stats {
  total: number;
  published: number;
  failed: number;
}

export default function BielPosts() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);

  useEffect(() => {
    fetch("/api/v1/biel/posts")
      .then(r => r.json())
      .then(setPosts)
      .catch(() => {});
    fetch("/api/v1/biel/stats")
      .then(r => r.json())
      .then(setStats)
      .catch(() => {});
  }, []);

  const statusColor = (s: string) => ({ published: "#00ff88", failed: "#ff4444", pending: "#ffd700" }[s] || "#888");
  const topicEmoji = (t: string) => ({ market: "📊", trade: "📈", insight: "💡", news: "📰" }[t] || "📌");

  return (
    <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 14 }}>📋 Histórico de Posts</div>
        {stats && (
          <div style={{ display: "flex", gap: 10, fontSize: 11 }}>
            <span style={{ color: "#888" }}>Total: <b style={{ color: "#c8d8e8" }}>{stats.total}</b></span>
            <span style={{ color: "#00ff88" }}>✅ {stats.published}</span>
            <span style={{ color: "#ff4444" }}>❌ {stats.failed}</span>
          </div>
        )}
      </div>

      {posts.length === 0 && (
        <div style={{ color: "#3d5a80", fontSize: 12, textAlign: "center", padding: 20 }}>
          Nenhum post ainda. Configure o Biel e force um post manual.
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 6, maxHeight: 500, overflowY: "auto" }}>
        {posts.map(p => (
          <div key={p.id}
            onClick={() => setExpanded(expanded === p.id ? null : p.id)}
            style={{
              background: "#060d1a", borderRadius: 8, padding: "10px 12px",
              border: `1px solid ${statusColor(p.status)}22`,
              cursor: "pointer", transition: "border-color 0.2s",
            }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 16 }}>{topicEmoji(p.topic || "")}</span>
                <div>
                  <div style={{ color: "#c8d8e8", fontSize: 12, fontWeight: 600 }}>
                    {p.topic?.charAt(0).toUpperCase()}{p.topic?.slice(1)}
                    {p.regime && <span style={{ color: "#3d5a80", fontSize: 10, marginLeft: 8 }}>{p.regime}</span>}
                  </div>
                  <div style={{ color: "#3d5a80", fontSize: 10 }}>
                    {p.published_at
                      ? new Date(p.published_at).toLocaleString("pt-BR")
                      : p.created_at ? new Date(p.created_at).toLocaleString("pt-BR") : "—"}
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                {p.pnl_snapshot !== null && (
                  <span style={{ color: p.pnl_snapshot >= 0 ? "#00ff88" : "#ff4444", fontSize: 11 }}>
                    {p.pnl_snapshot >= 0 ? "+" : ""}${p.pnl_snapshot?.toFixed(2)}
                  </span>
                )}
                <span style={{
                  fontSize: 10, padding: "2px 8px", borderRadius: 12,
                  background: statusColor(p.status) + "22",
                  color: statusColor(p.status), fontWeight: 700,
                }}>
                  {p.status.toUpperCase()}
                </span>
              </div>
            </div>

            {expanded === p.id && (
              <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid #141c2e", display: "flex", flexDirection: "column", gap: 6 }}>
                {p.caption && (
                  <div style={{ color: "#8899aa", fontSize: 11, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>
                    {p.caption}
                  </div>
                )}
                {p.instagram_id && (
                  <div style={{ color: "#3d5a80", fontSize: 10 }}>
                    Instagram ID: <span style={{ color: "#60a5fa" }}>{p.instagram_id}</span>
                  </div>
                )}
                {p.error && (
                  <div style={{ color: "#ff4444", fontSize: 10, background: "#2a0a0a", padding: "6px 8px", borderRadius: 6 }}>
                    {p.error}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
