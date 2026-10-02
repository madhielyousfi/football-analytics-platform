/** @type {import('tailwindcss').Config} */
export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#070B12",
        surface: "#0F1622",
        surface2: "#151D2A",
        line: "rgba(255,255,255,0.08)",
        muted: "#94A3B8",
        faint: "#64748B",
        pitch: "#22C55E",
        cyanx: "#06B6D4",
        violetx: "#8B5CF6",
        amberx: "#F59E0B",
        redx: "#EF4444",
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
      borderRadius: { xl2: "1rem", xl3: "1.25rem" },
      boxShadow: { card: "0 8px 30px rgba(0,0,0,0.35)" },
    },
  },
  plugins: [],
};
