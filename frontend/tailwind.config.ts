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
        // TradeAI Cockpit — Paleta institucional
        bg: {
          primary: "#050816",
          secondary: "#080c1a",
          tertiary: "#0d1426",
          card: "#0a0f1e",
          "card-hover": "#0d1426",
        },
        border: {
          primary: "#1a2a4a",
          secondary: "#14203a",
          "glow-blue": "#2a5fc8",
          "glow-green": "#1a7f4a",
          "glow-purple": "#5a2a8a",
        },
        text: {
          primary: "#e8ecf4",
          secondary: "#8b99b8",
          muted: "#4a5a7a",
          dim: "#3a4a6a",
        },
        neon: {
          blue: "#3b82f6",
          "blue-glow": "#60a5fa",
          green: "#10b981",
          "green-glow": "#34d399",
          purple: "#8b5cf6",
          "purple-glow": "#a78bfa",
          amber: "#f59e0b",
          red: "#ef4444",
          "red-glow": "#f87171",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
        display: ["Space Grotesk", "Inter", "sans-serif"],
      },
      fontSize: {
        "xs-mono": ["10px", { lineHeight: "1.4" }],
        "sm-mono": ["11px", { lineHeight: "1.4" }],
        "base-mono": ["12px", { lineHeight: "1.45" }],
        "lg-mono": ["13px", { lineHeight: "1.4" }],
        "xl-mono": ["14px", { lineHeight: "1.4" }],
      },
      spacing: {
        "xs": "2px",
        "sm": "4px",
        "md": "8px",
        "lg": "12px",
        "xl": "16px",
        "2xl": "24px",
      },
      borderRadius: {
        "sm": "4px",
        "md": "8px",
        "lg": "12px",
        "xl": "16px",
      },
      boxShadow: {
        "card": "0 4px 24px rgba(0,0,0,0.4), 0 0 0 1px #1a2a4a",
        "card-hover": "0 8px 32px rgba(0,0,0,0.5), 0 0 0 1px #2a5fc8, 0 0 20px rgba(59,130,246,0.15)",
        "glow-blue": "0 0 20px rgba(59,130,246,0.15), 0 0 40px rgba(59,130,246,0.08)",
        "glow-green": "0 0 20px rgba(16,185,129,0.15), 0 0 40px rgba(16,185,129,0.08)",
        "glow-purple": "0 0 20px rgba(139,92,246,0.15), 0 0 40px rgba(139,92,246,0.08)",
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "slide-up": "slide-up 0.4s cubic-bezier(0.4,0,0.2,1) forwards",
        "fade-in": "fade-in 0.5s ease-out forwards",
        "counter": "counter 0.6s cubic-bezier(0.4,0,0.2,1) forwards",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 8px currentColor" },
          "50%": { opacity: "0.6", boxShadow: "0 0 20px currentColor" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "counter": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "mesh-gradient": "linear-gradient(135deg, #050816 0%, #0d1426 50%, #0a0f1e 100%)",
      },
    },
  },
  plugins: [],
};

export default config;