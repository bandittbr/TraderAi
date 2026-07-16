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
        background: "#050816",
        surface: "#080c14",
        "surface-2": "#0d1525",
        border: "#1a2540",
        primary: "#3b82f6",
        "primary-neon": "#60a5fa",
        success: "#10b981",
        warning: "#f59e0b",
        danger: "#ef4444",
        muted: "#2d4060",
        "text-primary": "#f1f5f9",
        "text-secondary": "#8aa4c8",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        "slide-in": "slide-in 0.4s ease-out",
        "fade-in": "fade-in 0.6s ease-out",
      },
      boxShadow: {
        "neon-blue": "0 0 15px rgba(59, 130, 246, 0.3)",
        "neon-green": "0 0 15px rgba(16, 185, 129, 0.3)",
        "neon-purple": "0 0 15px rgba(139, 92, 246, 0.3)",
      },
    },
  },
  plugins: [],
};

export default config;
