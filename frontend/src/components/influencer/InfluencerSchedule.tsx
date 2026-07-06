"use client";

interface Slot {
  hour: number;
  label: string;
  done: boolean;
  is_next: boolean;
  is_past: boolean;
  post_type?: "image" | "reel";
}

interface ScheduleProps {
  slots: Slot[];
  nextLabel: string | null;
  nextMinutes: number | null;
}

export default function InfluencerSchedule({ slots, nextLabel, nextMinutes }: ScheduleProps) {
  return (
    <div style={{
      background: "#0d1525",
      border: "1px solid #141c2e",
      borderRadius: 12,
      padding: 20,
    }}>
      <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 14, marginBottom: 16 }}>
        📅 Agenda de Hoje
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 10 }}>
        {slots.map(slot => {
          const bgColor =
            slot.done ? "#0a2a1a" :
            slot.is_next ? "#1a1a00" :
            slot.is_past ? "#2a0a0a" : "#060d1a";
          const borderColor =
            slot.done ? "#00ff8844" :
            slot.is_next ? "#ffd70044" :
            slot.is_past ? "#ff444433" : "#141c2e";
          const labelColor =
            slot.done ? "#00ff88" :
            slot.is_next ? "#ffd700" :
            slot.is_past ? "#ff6644" : "#3d5a80";
          const icon =
            slot.done ? "✅" :
            slot.is_next ? "⏳" :
            slot.is_past ? "⚠️" : "🔲";

          return (
            <div key={slot.hour} style={{
              background: bgColor,
              border: `1px solid ${borderColor}`,
              borderRadius: 10,
              padding: "14px 10px",
              textAlign: "center",
              position: "relative",
            }}>
              {slot.is_next && (
                <div style={{
                  position: "absolute", top: -8, left: "50%", transform: "translateX(-50%)",
                  fontSize: 9, background: "#ffd700", color: "#000",
                  padding: "1px 8px", borderRadius: 10, fontWeight: 700, whiteSpace: "nowrap",
                }}>
                  PRÓXIMO
                </div>
              )}
              <div style={{ fontSize: 20 }}>{icon}</div>
              {slot.post_type === "reel" && (
                <div style={{ fontSize: 8, color: "#c084fc", background: "#2a1a4a", border: "1px solid #8b5cf644", padding: "1px 6px", borderRadius: 6, display: "inline-block", marginTop: 4 }}>
                  REEL
                </div>
              )}
              <div style={{ color: labelColor, fontSize: 15, fontWeight: 800, marginTop: 6 }}>
                {slot.label}
              </div>
              <div style={{ color: labelColor, fontSize: 10, marginTop: 4, opacity: 0.8 }}>
                {slot.done ? "Publicado" : slot.is_next ? (nextMinutes ? `em ${nextMinutes}min` : "em breve") : slot.is_past ? "Falhou" : "Aguardando"}
              </div>
            </div>
          );
        })}
      </div>

      {slots.length === 0 && (
        <div style={{ color: "#3d5a80", fontSize: 12, textAlign: "center", padding: 20 }}>
          Nenhum horário configurado. Configure o Biel primeiro.
        </div>
      )}
    </div>
  );
}
