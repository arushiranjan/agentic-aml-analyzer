import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "#0F172A",
        surface: "#111827",
        card: "rgba(255,255,255,0.04)",
        border: "rgba(255,255,255,0.08)",
        emerald: {
          DEFAULT: "#10B981",
        },
        amber: {
          DEFAULT: "#F59E0B",
        },
        cyan: {
          DEFAULT: "#22D3EE",
        },
        critical: {
          DEFAULT: "#F97316",
        },
        muted: "#94A3B8",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glass: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
export default config;
