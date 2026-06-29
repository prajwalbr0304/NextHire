import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#1a1f36", soft: "#3c4257", muted: "#697386", faint: "#8792a2" },
        // ChatGPT-style green brand system (centralised token — see globals.css :root)
        brand: {
          DEFAULT: "#10A37F", dark: "#0D8F6F", active: "#0B7A5E",
          light: "#34B794", wash: "#E7F8F3", lighter: "#F3FCF9",
          c2: "#5AC7A8", c3: "#87D9C1",
        },
        line: "#e3e8ee",
        canvas: "#f6f8fb",
        positive: "#0e9f6e",
        warn: "#d97706",
        danger: "#e25950",
      },
      boxShadow: {
        card: "0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06)",
        pop: "0 8px 28px rgba(16,24,40,.12)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
