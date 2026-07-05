"use client";

interface MetricsProps {
  counters: {
    total: number;
    published: number;
    failed: number;
    today: number;
    week: number;
    month: number;
    success_rate: number;
    days_active: number;
  };
  topics: Record<string, number>;
  daily: { date: string; count: number }[];
}

const TOPIC_META: Record<string, { label: string; color: string; emoji: string }> = {
  market:  { label: "Mercado",  color: "#60a5fa", emoji: "📊" },
  trade:   { label: "Trade",    color: "#00ff88", emoji: "📈" },
  insight: { label: "Insight",  color: "#ffd700", emoji: "💡" },
  news:    { label: "Notícia",  color: "#c084fc", emoji: "📰" },
};

export default function InfluencerMetrics({ counters, topics, daily }: MetricsProps) {
  const maxDaily = Math.max(...daily.map(d => d.count), 1);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

      {/* Counters grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
        {[
          { label: "Publicados",   value: counters.published, color: "#00ff88", sub: "total" },
          { label: "Esta semana",  value: counters.week,      color: "#60a5fa", sub: "posts" },
          { label: "Este mês",     value: counters.month,     color: "#c084fc", sub: "posts" },
          { label: "Taxa de sucesso", value: `${counters.success_rate}%`, color: counters.success_rate >= 80 ? "#00ff88" : counters.success_rate >= 50 ? "#ffd700" : "#ff4444", sub: "publicações" },
        ].map(({ label, value, color, sub }) => (
          <div key={label} style={{
            background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12,
            padding: "16px 14px", textAlign: "center",
          }}>
            <div style={{ color: "#3d5a80", fontSize: 10, textTransform: "uppercase", letterSpacing: 1 }}>{label}</div>
            <div style={{ color, fontSize: 28, fontWeight: 800, marginTop: 6, lineHeight: 1 }}>{value}</div>
            <div style={{ color: "#3d5a80", fontSize: 10, marginTop: 4 }}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Gráfico de barras — últimos 7 dias */}
      <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20 }}>
        <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 13, marginBottom: 16 }}>
          📊 Posts por Dia — Últimos 7 Dias
        </div>
        <div style={{ display: "flex", gap: 6, alignItems: "flex-end", height: 80 }}>
          {daily.map(d => {
            const pct = (d.count / maxDaily) * 100;
            const label = new Date(d.date + "T12:00:00Z").toLocaleDateString("pt-BR", { weekday: "short", day: "numeric" });
            return (
              <div key={d.date} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                <div style={{ fontSize: 10, color: "#60a5fa", fontWeight: 700 }}>
                  {d.count > 0 ? d.count : ""}
                </div>
                <div style={{
                  width: "100%", background: d.count > 0 ? "#2563eb" : "#141c2e",
                  borderRadius: "4px 4px 0 0",
                  height: `${Math.max(pct, d.count > 0 ? 8 : 2)}%`,
                  minHeight: 2, transition: "height 0.3s",
                }} />
                <div style={{ fontSize: 9, color: "#3d5a80", textAlign: "center" }}>{label}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Breakdown por tópico */}
      <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20 }}>
        <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 13, marginBottom: 14 }}>
          🎯 Posts por Tópico
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
          {["market", "trade", "insight", "news"].map(t => {
            const meta = TOPIC_META[t];
            const count = topics[t] || 0;
            const total = counters.published || 1;
            const pct = Math.round(count / total * 100);
            return (
              <div key={t} style={{
                background: "#060d1a", borderRadius: 10, padding: "12px 14px",
                border: `1px solid ${meta.color}22`,
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <span style={{ fontSize: 16 }}>{meta.emoji}</span>
                    <span style={{ color: meta.color, fontWeight: 700, fontSize: 13 }}>{meta.label}</span>
                  </div>
                  <span style={{ color: "#c8d8e8", fontWeight: 800, fontSize: 18 }}>{count}</span>
                </div>
                <div style={{ marginTop: 10, background: "#141c2e", borderRadius: 4, height: 4 }}>
                  <div style={{
                    width: `${pct}%`, height: "100%",
                    background: meta.color, borderRadius: 4,
                    transition: "width 0.5s",
                  }} />
                </div>
                <div style={{ color: "#3d5a80", fontSize: 10, marginTop: 4 }}>{pct}% do total</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
