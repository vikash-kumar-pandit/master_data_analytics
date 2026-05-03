/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#f0f9ff",
          100: "#e0f2fe",
          200: "#bae6fd",
          300: "#7dd3fc",
          400: "#38bdf8",
          500: "#0ea5e9",
          600: "#0284c7",
          700: "#0369a1",
          800: "#075985",
          900: "#0c3d66",
        },
        secondary: {
          50: "#f0fdf4",
          100: "#dcfce7",
          200: "#bbf7d0",
          300: "#86efac",
          400: "#4ade80",
          500: "#22c55e",
          600: "#16a34a",
          700: "#15803d",
          800: "#166534",
          900: "#145231",
        },
        accent: {
          50: "#fdf2f8",
          100: "#fce7f3",
          200: "#fbcfe8",
          300: "#f8a4d6",
          400: "#f472b6",
          500: "#ec4899",
          600: "#db2777",
          700: "#be185d",
          800: "#9d174d",
          900: "#831843",
        },
        neutral: {
          50: "#f9fafb",
          100: "#f3f4f6",
          200: "#e5e7eb",
          300: "#d1d5db",
          400: "#9ca3af",
          500: "#6b7280",
          600: "#4b5563",
          700: "#374151",
          800: "#1f2937",
          900: "#111827",
        },
      },
      fontFamily: {
        sans: ["Plus Jakarta Sans", "Manrope", "Segoe UI", "sans-serif"],
        mono: ["Fira Code", "monospace"],
      },
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1rem" }],
        sm: ["0.875rem", { lineHeight: "1.25rem" }],
        base: ["1rem", { lineHeight: "1.5rem" }],
        lg: ["1.125rem", { lineHeight: "1.75rem" }],
        xl: ["1.25rem", { lineHeight: "1.75rem" }],
        "2xl": ["1.5rem", { lineHeight: "2rem" }],
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],
        "4xl": ["2.25rem", { lineHeight: "2.5rem" }],
        "5xl": ["3rem", { lineHeight: "1" }],
      },
      borderRadius: {
        lg: "20px",
        md: "14px",
        sm: "10px",
      },
      spacing: {
        xs: "0.25rem",
        sm: "0.5rem",
        md: "1rem",
        lg: "1.5rem",
        xl: "2rem",
        "2xl": "3rem",
        "3xl": "4rem",
      },
      boxShadow: {
        soft: "0 22px 50px rgba(16, 31, 49, 0.08)",
        card: "0 14px 30px rgba(17, 33, 51, 0.08)",
        glow: "0 0 28px rgba(14, 165, 233, 0.32)",
        hover: "0 25px 50px rgba(16, 31, 49, 0.15)",
      },
      backdropBlur: {
        xs: "2px",
        sm: "4px",
        md: "8px",
        lg: "12px",
        xl: "16px",
      },
      animation: {
        "aurora-drift": "auroraDrift 22s ease-in-out infinite",
        "glow-pulse": "glowPulse 2s ease-in-out infinite",
        "rise-in": "riseIn 0.6s ease-out",
        "border-scan": "borderScan 3s ease-in-out infinite",
      },
      keyframes: {
        auroraDrift: {
          "0%": {
            backgroundPosition: "0% 0%, 100% 10%, 55% 100%, 0% 0%",
          },
          "50%": {
            backgroundPosition: "8% 6%, 92% 2%, 62% 92%, 0% 0%",
          },
          "100%": {
            backgroundPosition: "0% 0%, 100% 10%, 55% 100%, 0% 0%",
          },
        },
        glowPulse: {
          "0%": {
            boxShadow: "0 0 0 rgba(14, 165, 233, 0)",
          },
          "50%": {
            boxShadow: "0 0 28px rgba(14, 165, 233, 0.32)",
          },
          "100%": {
            boxShadow: "0 0 0 rgba(14, 165, 233, 0)",
          },
        },
        riseIn: {
          "0%": {
            opacity: "0",
            transform: "translateY(16px)",
          },
          "100%": {
            opacity: "1",
            transform: "translateY(0)",
          },
        },
        borderScan: {
          "0%": {
            transform: "translateX(-120%)",
          },
          "100%": {
            transform: "translateX(180%)",
          },
        },
      },
    },
  },
  plugins: [
    require("@tailwindcss/forms"),
  ],
}
