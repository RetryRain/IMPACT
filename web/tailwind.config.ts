import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#1a1a1a",
        paper: "#faf9f7",
        accent: "#3d7a5c",
        "accent-soft": "#e8f3ec",
        "accent-ink": "#2a5c44",
        visited: "#6b3fa0",
        muted: "#6b6560",
        border: "#e8e4de",
        "scope-tn-bg": "#f4e4d4",
        "scope-tn-text": "#7a3f24",
        "scope-india-bg": "#dce8f4",
        "scope-india-text": "#1a3d66",
        "scope-world-bg": "#ddeee8",
        "scope-world-text": "#2a5560",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      maxWidth: {
        article: "42rem",
      },
    },
  },
  plugins: [],
  safelist: [
    "bg-scope-tn-bg",
    "text-scope-tn-text",
    "bg-scope-india-bg",
    "text-scope-india-text",
    "bg-scope-world-bg",
    "text-scope-world-text",
  ],
};

export default config;
