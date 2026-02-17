import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f5fbff",
          100: "#e8f6ff",
          600: "#005f8f",
          700: "#004e75"
        }
      }
    }
  },
  plugins: []
};

export default config;
