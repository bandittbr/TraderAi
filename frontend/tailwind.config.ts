import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta TradeAI — tema escuro financeiro
        background: "#0a0e1a",
        surface: "#111827",
        "surface-2": "#1f2937",
        border: "#1f2937",
        primary: "#3b82f6",
        "primary-hover": "#2563eb",
        success: "#10b981",
        warning: "#f59e0b",
        danger: "#ef4444",
        muted: "#6b7280",
        "text-primary": "#f9fafb",
        "text-secondary": "#9ca3af",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
      },
    },
  },
  plugins: [],
};

export default config;
