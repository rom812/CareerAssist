import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "var(--background)",
                foreground: "var(--foreground)",
                primary: "var(--color-primary)",
                "ai-accent": "var(--color-ai-accent)",
                accent: "var(--color-accent)",
                dark: "var(--color-dark)",
                success: "var(--color-success)",
                error: "var(--color-error)",
            },
            fontFamily: {
                sans: ["var(--font-sans)", "system-ui", "sans-serif"],
                mono: ["var(--font-mono)", "monospace"],
            },
            animation: {
                "strong-pulse": "strong-pulse 1.5s cubic-bezier(0.4, 0, 0.6, 1) infinite",
                "glow-pulse": "glow-pulse 1.5s ease-in-out infinite",
                "slide-in": "slide-in 0.3s ease-out",
            },
            keyframes: {
                "strong-pulse": {
                    "0%, 100%": { opacity: "1", transform: "scale(1)" },
                    "50%": { opacity: "0.4", transform: "scale(0.95)" },
                },
                "glow-pulse": {
                    "0%, 100%": {
                        opacity: "1",
                        boxShadow: "0 0 20px rgba(117, 57, 145, 0.5), 0 0 40px rgba(117, 57, 145, 0.3)"
                    },
                    "50%": {
                        opacity: "0.7",
                        boxShadow: "0 0 30px rgba(117, 57, 145, 0.8), 0 0 60px rgba(117, 57, 145, 0.5)"
                    },
                },
                "slide-in": {
                    "from": { transform: "translateX(100%)", opacity: "0" },
                    "to": { transform: "translateX(0)", opacity: "1" },
                },
            },
        },
    },
    plugins: [],
};
export default config;
