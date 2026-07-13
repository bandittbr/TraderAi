"use client";
import { useCallback, useEffect, useState } from "react";
import InfluencerHero     from "@/components/influencer/InfluencerHero";
import InfluencerSchedule from "@/components/influencer/InfluencerSchedule";
import InfluencerMetrics  from "@/components/influencer/InfluencerMetrics";
import InfluencerFeed     from "@/components/influencer/InfluencerFeed";
import InfluencerReelsFeed from "@/components/influencer/InfluencerReelsFeed";
import InfluencerControls from "@/components/influencer/InfluencerControls";
import InfluencerEngagement from "@/components/influencer/InfluencerEngagement";
import BielSetup          from "@/components/biel/BielSetup";

export default function InfluencerPage() {
  const [metrics, setMetrics]   = useState<any>(null);
  const [posts, setPosts]       = useState<any[]>([]);
  const [loading, setLoading]   = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [tab, setTab] = useState<"overview" | "engagement" | "feed" | "reels" | "setup">("overview");

  const refresh = useCallback(async () => {
    try {
      const [m, p] = await Promise.all([
        fetch("/api/v1/biel/metrics").then(r => r.json()),
        fetch("/api/v1/biel/posts?limit=100").then(r => r.json()),
      ]);
      setMetrics(m);
      setPosts(Array.isArray(p) ? p : []);
      setLastUpdate(new Date());
    } catch (e) {
      console.error("Erro ao carregar métricas do Biel:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, [refresh]);

  const tabs = [
    { key: "overview",   label: "📊 Overview" },
    { key: "engagement", label: "⚡ Engajamento" },
    { key: "feed",       label: "📋 Feed de Posts" },
    { key: "reels",      label: "🎬 Reels" },
    { key: "setup",      label: "🔧 Configurar" },
  ] as const;

  if (loading) {
    return (
      <div className="p-6 max-w-[1400px] mx-auto">
        <div style={{ color: "#3d5a80", fontSize: 14, textAlign: "center", marginTop: 60 }}>
          Carregando Influencer Dashboard...
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-5 max-w-[1400px] mx-auto">

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 style={{ color: "#ffd700", fontWeight: 900, fontSize: 22 }}>⚡ Influencer Dashboard</h1>
          <p style={{ color: "#3d5a80", fontSize: 11, marginTop: 4 }}>
            Biel Agent · Publicações autônomas no Instagram · Gemini 2.0 Flash · Dados reais do TradeAI
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          {lastUpdate && (
            <span style={{ color: "#1e3a5f", fontSize: 10 }}>
              Atualizado {lastUpdate.toLocaleTimeString("pt-BR")}
            </span>
          )}
          <button onClick={refresh} style={{
            background: "#1e3a5f", color: "#60a5fa", border: "1px solid #2563eb",
            borderRadius: 8, padding: "6px 14px", fontSize: 11, cursor: "pointer",
          }}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Hero */}
      {metrics && <InfluencerHero metrics={metrics} />}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 6 }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            style={{
              fontSize: 12, padding: "7px 18px", borderRadius: 8, cursor: "pointer",
              background: tab === t.key ? "#1e3a5f" : "#0d1525",
              color:      tab === t.key ? "#60a5fa" : "#3d5a80",
              border:     `1px solid ${tab === t.key ? "#2563eb" : "#141c2e"}`,
              transition: "all 0.2s",
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab: Overview */}
      {tab === "overview" && metrics && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

            {/* Agenda do dia */}
            <InfluencerSchedule
              slots={metrics.schedule?.slots || []}
              nextLabel={metrics.schedule?.next_post_label}
              nextMinutes={metrics.schedule?.next_post_in_minutes}
            />

            {/* Métricas */}
            <InfluencerMetrics
              counters={metrics.counters}
              topics={metrics.topics || {}}
              reel_topics={metrics.reel_topics || {}}
              daily={metrics.daily || []}
            />

            {/* Último post */}
            {metrics.last_post && (
              <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20 }}>
                <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 13, marginBottom: 12 }}>
                  🕐 Último Post Publicado
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <span style={{ fontSize: 16 }}>
                      {metrics.last_post.post_type === "reel" ? "🎬"
                        : metrics.last_post.topic === "market" ? "📊"
                        : metrics.last_post.topic === "trade" ? "📈"
                        : metrics.last_post.topic === "insight" ? "💡" : "📰"}
                    </span>
                    <span style={{ color: "#c8d8e8", fontWeight: 700, fontSize: 13, textTransform: "capitalize" }}>
                      {metrics.last_post.reel_topic || metrics.last_post.topic}
                    </span>
                    {metrics.last_post.post_type === "reel" && (
                      <span style={{ fontSize: 9, color: "#c084fc", background: "#2a1a4a", border: "1px solid #8b5cf6", padding: "1px 6px", borderRadius: 6 }}>
                        REEL
                      </span>
                    )}
                    {metrics.last_post.regime && (
                      <span style={{ fontSize: 10, color: "#3d5a80", background: "#141c2e", padding: "1px 8px", borderRadius: 6 }}>
                        {metrics.last_post.regime}
                      </span>
                    )}
                    {metrics.last_post.pnl_snapshot !== null && (
                      <span style={{ color: metrics.last_post.pnl_snapshot >= 0 ? "#00ff88" : "#ff4444", fontSize: 12, fontWeight: 700 }}>
                        {metrics.last_post.pnl_snapshot >= 0 ? "+" : ""}${metrics.last_post.pnl_snapshot?.toFixed(2)}
                      </span>
                    )}
                  </div>
                  {metrics.last_post.caption_preview && (
                    <div style={{ color: "#8899aa", fontSize: 12, lineHeight: 1.5, background: "#060d1a", padding: "10px 12px", borderRadius: 8 }}>
                      {metrics.last_post.caption_preview}
                    </div>
                  )}
                  <div style={{ color: "#3d5a80", fontSize: 10 }}>
                    {metrics.last_post.published_at
                      ? new Date(metrics.last_post.published_at).toLocaleString("pt-BR")
                      : "—"}
                    {metrics.last_post.instagram_id && (
                      <span style={{ color: "#60a5fa", marginLeft: 10 }}>IG: {metrics.last_post.instagram_id}</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Coluna direita: Controles */}
          <div>
            <InfluencerControls
              status={metrics.status}
              onRefresh={refresh}
            />
          </div>
        </div>
      )}

      {/* Tab: Feed */}
      {tab === "feed" && (
        <InfluencerFeed posts={posts} />
      )}

      {/* Tab: Engagement */}
      {tab === "engagement" && (
        <InfluencerEngagement />
      )}

      {/* Tab: Reels */}
      {tab === "reels" && (
        <InfluencerReelsFeed posts={posts} />
      )}

      {/* Tab: Setup */}
      {tab === "setup" && (
        <div style={{ maxWidth: 520 }}>
          <BielSetup onSetupDone={() => { refresh(); setTab("overview"); }} />
        </div>
      )}
    </div>
  );
}
