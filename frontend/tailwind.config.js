/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        shell: {
          950: "#111827",
          900: "#172033",
          800: "#22304a",
          100: "#edf4ff",
        },
        accent: {
          blue: "#2563eb",
          mint: "#14b8a6",
          gold: "#eab308",
          coral: "#f97316",
        },
      },
      boxShadow: {
        board: "0 24px 60px rgba(15, 23, 42, 0.18)",
      },
      borderRadius: {
        xl2: "1.5rem",
      },
    },
  },
  plugins: [],
};
