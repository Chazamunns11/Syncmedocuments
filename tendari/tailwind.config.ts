import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        forest: "#1F6B4C",
        "deep-green": "#134E37",
        sage: "#8FB7A3",
        mint: "#E4EFE7",
        canvas: "#F2F4EC",
        ink: "#14281F",
        muted: "#5B6B61",
      },
      fontFamily: {
        sans: [
          "ui-rounded",
          "'Segoe UI'",
          "Nunito",
          "Poppins",
          "system-ui",
          "-apple-system",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
      boxShadow: {
        soft: "0 1px 2px rgba(19,78,55,0.04), 0 8px 24px rgba(19,78,55,0.06)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
      },
    },
  },
  plugins: [],
};

export default config;
