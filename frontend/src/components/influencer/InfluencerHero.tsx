"use client";

interface HeroProps {
  metrics: any;
}

function Countdown({ minutes }: { minutes: number | null }) {
  if (minutes === null) return <span style={{ color: "#3d5a80" }}>—</span>;
  if (minutes <= 0) return <span style={{ color: "#00ff88" }}>Agora</span>;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  const label = h > 0 ? `${h}h ${m}m` : `${m}m`;
  return <span style={{ color: "#ffd700" }}>{label}</span>;
}

export default function InfluencerHero({ metrics }: HeroProps) {
  if (!metrics) return null;
  const { status, counters, schedule } = metrics;

  const isLive = status.configured && status.token_active && status.active;
  const tokenDays = status.token_days_left;
  const tokenColor =
    tokenDays === null ? "#888" :
    tokenDays <= 7 ? "#ff4444" :
    tokenDays <= 14 ? "#ffd700" : "#00ff88";

  return (
    <div style={{
      background: "linear-gradient(135deg, #0d1525 0%, #0a1020 50%, #080c18 100%)",
      border: "1px solid #1e3a5f",
      borderRadius: 16,
      padding: "28px 32px",
      display: "flex",
      gap: 32,
      alignItems: "center",
      flexWrap: "wrap",
    }}>
      {/* Avatar + identidade */}
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{
          width: 80, height: 80, borderRadius: "50%",
          background: "linear-gradient(135deg, #ffd700, #ff8c00)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 36, boxShadow: "0 0 24px #ffd70044",
          flexShrink: 0,
        }}>
          ⚡
        </div>
        <div>
          <div style={{ color: "#ffd700", fontSize: 26, fontWeight: 900, lineHeight: 1 }}>
            {status.persona_name || "Biel"}
          </div>
          <div style={{ color: "#3d5a80", fontSize: 12, marginTop: 4 }}>
            Instagram Agent · Groq / Gemini
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 8, alignItems: "center" }}>
            <div style={{
              fontSize: 11, padding: "3px 12px", borderRadius: 20, fontWeight: 700,
              background: isLive ? "#00ff8822" : "#ff444422",
              color: isLive ? "#00ff88" : "#ff4444",
              border: `1px solid ${isLive ? "#00ff8844" : "#ff444444"}`,
            }}>
              {isLive ? "● ONLINE" : "● OFFLINE"}
            </div>
            {counters.days_active > 0 && (
              <div style={{ fontSize: 10, color: "#3d5a80" }}>
                {counters.days_active} {counters.days_active === 1 ? "dia" : "dias"} ativo
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Divider */}
      <div style={{ width: 1, height: 70, background: "#1e3a5f", flexShrink: 0 }} />

      {/* Próximo post */}
      <div style={{ textAlign: "center" }}>
        <div style={{ color: "#3d5a80", fontSize: 10, textTransform: "uppercase", letterSpacing: 1 }}>Próximo post</div>
        <div style={{ fontSize: 28, fontWeight: 800, lineHeight: 1.2, marginTop: 6 }}>
          <Countdown minutes={schedule?.next_post_in_minutes ?? null} />
        </div>
        {schedule?.next_post_label && (
          <div style={{ color: "#3d5a80", fontSize: 11, marginTop: 4 }}>{schedule.next_post_label}</div>
        )}
      </div>

      {/* Divider */}
      <div style={{ width: 1, height: 70, background: "#1e3a5f", flexShrink: 0 }} />

      {/* Posts hoje */}
      <div style={{ textAlign: "center" }}>
        <div style={{ color: "#3d5a80", fontSize: 10, textTransform: "uppercase", letterSpacing: 1 }}>Hoje</div>
        <div style={{ fontSize: 28, fontWeight: 800, color: "#60a5fa", marginTop: 6 }}>
          {counters.today}<span style={{ color: "#1e3a5f", fontSize: 16 }}>/{status.posts_per_day}</span>
        </div>
        <div style={{ color: "#3d5a80", fontSize: 11, marginTop: 4 }}>posts</div>
      </div>

      {/* Divider */}
      <div style={{ width: 1, height: 70, background: "#1e3a5f", flexShrink: 0 }} />

      {/* Total publicados */}
      <div style={{ textAlign: "center" }}>
        <div style={{ color: "#3d5a80", fontSize: 10, textTransform: "uppercase", letterSpacing: 1 }}>Total</div>
        <div style={{ fontSize: 28, fontWeight: 800, color: "#00ff88", marginTop: 6 }}>{counters.published}</div>
        <div style={{ color: "#3d5a80", fontSize: 11, marginTop: 4 }}>publicados</div>
      </div>

      {/* Divider */}
      <div style={{ width: 1, height: 70, background: "#1e3a5f", flexShrink: 0 }} />

      {/* Token */}
      <div style={{ textAlign: "center" }}>
        <div style={{ color: "#3d5a80", fontSize: 10, textTransform: "uppercase", letterSpacing: 1 }}>Token IG</div>
        <div style={{ fontSize: 24, fontWeight: 800, color: tokenColor, marginTop: 6 }}>
          {tokenDays !== null ? `${tokenDays}d` : "—"}
        </div>
        <div style={{ color: "#3d5a80", fontSize: 11, marginTop: 4 }}>restantes</div>
      </div>

      {/* Conta Instagram */}
      {status.instagram_account_id && (
        <>
          <div style={{ width: 1, height: 70, background: "#1e3a5f", flexShrink: 0 }} />
          <div style={{ textAlign: "center" }}>
            <div style={{ color: "#3d5a80", fontSize: 10, textTransform: "uppercase", letterSpacing: 1 }}>Conta IG</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#c8d8e8", marginTop: 8, fontFamily: "monospace" }}>
              {status.instagram_account_id.slice(0, 8)}…
            </div>
            <div style={{ color: "#3d5a80", fontSize: 11, marginTop: 4 }}>account ID</div>
          </div>
        </>
      )}
    </div>
  );
}
