"use client";
import { useState } from "react";

export default function BielSetup({ onSetupDone }: { onSetupDone?: () => void }) {
  const [form, setForm] = useState({
    gemini_api_key: "",
    access_token: "",
    app_id: "",
    app_secret: "",
    post_hours: "8,12,18,22",
  });
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState("");

  const handleSubmit = async () => {
    if (!form.gemini_api_key || !form.access_token || !form.app_id || !form.app_secret) {
      setMsg("❌ Preencha todos os campos obrigatórios.");
      return;
    }
    setLoading(true);
    setMsg("");
    try {
      const r = await fetch("/api/v1/biel/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gemini_api_key: form.gemini_api_key,
          access_token:   form.access_token,
          app_id:         form.app_id,
          app_secret:     form.app_secret,
          post_hours:     form.post_hours,
          posts_per_day:  form.post_hours.split(",").length,
        }),
      });
      const j = await r.json();
      if (r.ok) {
        setMsg(`✅ Biel configurado! Conta IG: ${j.instagram_account_id}`);
        onSetupDone?.();
      } else {
        setMsg(`❌ ${j.detail || "Erro desconhecido"}`);
      }
    } catch {
      setMsg("❌ Erro de conexão com o backend");
    }
    setLoading(false);
  };

  const field = (label: string, key: keyof typeof form, placeholder: string, type = "text") => (
    <div key={key} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      <label style={{ color: "#3d5a80", fontSize: 10, textTransform: "uppercase" }}>{label}</label>
      <input
        type={type}
        value={form[key]}
        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
        placeholder={placeholder}
        style={{
          background: "#060d1a", border: "1px solid #141c2e", borderRadius: 8,
          color: "#c8d8e8", fontSize: 12, padding: "8px 10px", outline: "none",
          fontFamily: "monospace",
        }}
      />
    </div>
  );

  return (
    <div style={{ background: "#0d1525", border: "1px solid #141c2e", borderRadius: 12, padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
      <div>
        <div style={{ color: "#60a5fa", fontWeight: 700, fontSize: 14 }}>🔧 Configurar Biel</div>
        <div style={{ color: "#3d5a80", fontSize: 11, marginTop: 2 }}>Setup inicial — credenciais são salvas no banco de dados do servidor</div>
      </div>

      {field("AI API Key (Groq gsk_... ou Gemini AIza/AQ.)", "gemini_api_key", "gsk_... ou AIza...", "password")}
      {field("Instagram Access Token", "access_token", "EAAX...", "password")}
      {field("Facebook App ID", "app_id", "1654543728935583")}
      {field("Facebook App Secret", "app_secret", "dca45c43...", "password")}

      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        <label style={{ color: "#3d5a80", fontSize: 10, textTransform: "uppercase" }}>Horários dos Posts (UTC)</label>
        <input
          value={form.post_hours}
          onChange={e => setForm(f => ({ ...f, post_hours: e.target.value }))}
          placeholder="8,12,18,22"
          style={{
            background: "#060d1a", border: "1px solid #141c2e", borderRadius: 8,
            color: "#c8d8e8", fontSize: 12, padding: "8px 10px", outline: "none",
          }}
        />
        <div style={{ color: "#3d5a80", fontSize: 9 }}>
          Separados por vírgula. Exemplo: 8,12,18,22 = 4 posts por dia (horário UTC)
        </div>
      </div>

      <button
        onClick={handleSubmit}
        disabled={loading}
        style={{
          background: loading ? "#1e3a5f88" : "#1e3a5f",
          color: "#60a5fa", border: "1px solid #2563eb",
          borderRadius: 8, padding: "10px 0", fontSize: 13,
          fontWeight: 700, cursor: loading ? "not-allowed" : "pointer",
        }}>
        {loading ? "Configurando..." : "Salvar Configuração"}
      </button>

      {msg && (
        <div style={{
          fontSize: 11, padding: "8px 12px", borderRadius: 8,
          background: msg.startsWith("✅") ? "#0a2a1a" : "#2a0a0a",
          color: msg.startsWith("✅") ? "#00ff88" : "#ff4444",
          border: `1px solid ${msg.startsWith("✅") ? "#00ff4422" : "#ff444422"}`,
        }}>
          {msg}
        </div>
      )}
    </div>
  );
}
