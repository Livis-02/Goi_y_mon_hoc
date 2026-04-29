/* tailwind-config.js — EduGuide design tokens (Material 3 + Inter)
   Load this file BEFORE the Tailwind CDN script, e.g.:
     <script src="tailwind-config.js"></script>
     <script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
*/
(function () {
  const cfg = {
    darkMode: "class",
    theme: {
      extend: {
        colors: {
          background: "#f8f9ff",
          "on-background": "#0b1c30",
          surface: "#f8f9ff",
          "on-surface": "#0b1c30",
          "on-surface-variant": "#474651",
          "surface-bright": "#f8f9ff",
          "surface-dim": "#cbdbf5",
          "surface-variant": "#d3e4fe",
          "surface-container-lowest": "#ffffff",
          "surface-container-low": "#eff4ff",
          "surface-container": "#e5eeff",
          "surface-container-high": "#dce9ff",
          "surface-container-highest": "#d3e4fe",
          "surface-tint": "#5654a8",
          "inverse-surface": "#213145",
          "inverse-on-surface": "#eaf1ff",
          outline: "#777682",
          "outline-variant": "#c8c5d3",
          primary: "#1a146b",
          "on-primary": "#ffffff",
          "primary-container": "#312e81",
          "on-primary-container": "#9c9af4",
          "primary-fixed": "#e2dfff",
          "primary-fixed-dim": "#c3c0ff",
          "on-primary-fixed": "#100563",
          "on-primary-fixed-variant": "#3e3c8f",
          "inverse-primary": "#c3c0ff",
          secondary: "#006c49",
          "on-secondary": "#ffffff",
          "secondary-container": "#6cf8bb",
          "on-secondary-container": "#00714d",
          "secondary-fixed": "#6ffbbe",
          "secondary-fixed-dim": "#4edea3",
          "on-secondary-fixed": "#002113",
          "on-secondary-fixed-variant": "#005236",
          tertiary: "#0a0086",
          "on-tertiary": "#ffffff",
          "tertiary-container": "#1e19b2",
          "on-tertiary-container": "#979aff",
          "tertiary-fixed": "#e1e0ff",
          "tertiary-fixed-dim": "#c0c1ff",
          "on-tertiary-fixed": "#07006c",
          "on-tertiary-fixed-variant": "#2f2ebe",
          error: "#ba1a1a",
          "on-error": "#ffffff",
          "error-container": "#ffdad6",
          "on-error-container": "#93000a",
        },
        borderRadius: {
          DEFAULT: "0.125rem",
          lg: "0.25rem",
          xl: "0.5rem",
          "2xl": "0.75rem",
          full: "9999px",
        },
        spacing: {
          xs: "4px",
          base: "4px",
          sm: "8px",
          md: "16px",
          lg: "24px",
          xl: "32px",
          "2xl": "48px",
          gutter: "24px",
          margin: "32px",
        },
        fontFamily: {
          sans: ["Inter", "system-ui", "sans-serif"],
          h1: ["Inter"],
          h2: ["Inter"],
          h3: ["Inter"],
          "body-lg": ["Inter"],
          "body-md": ["Inter"],
          "body-sm": ["Inter"],
          "label-md": ["Inter"],
          "label-sm": ["Inter"],
        },
        fontSize: {
          "body-lg": ["18px", { lineHeight: "1.6", fontWeight: "400" }],
          "body-md": ["16px", { lineHeight: "1.5", fontWeight: "400" }],
          "body-sm": ["14px", { lineHeight: "1.5", fontWeight: "400" }],
          "label-md": ["14px", { lineHeight: "1.2", fontWeight: "600" }],
          "label-sm": ["12px", { lineHeight: "1.2", fontWeight: "500" }],
          h1: ["36px", { lineHeight: "1.2", letterSpacing: "-0.02em", fontWeight: "700" }],
          h2: ["30px", { lineHeight: "1.3", letterSpacing: "-0.01em", fontWeight: "600" }],
          h3: ["24px", { lineHeight: "1.3", fontWeight: "600" }],
        },
      },
    },
  };

  // Set both for the CDN runtime to pick up regardless of load order.
  if (typeof window !== "undefined") {
    window.tailwind = window.tailwind || {};
    window.tailwind.config = cfg;
  }
})();
