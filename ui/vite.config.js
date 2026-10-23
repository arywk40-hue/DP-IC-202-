import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

// This config packages the dashboard as an installable, offline-first PWA —
// per the project's design requirement that the admin device works even
// when disconnected from the Master Node's WiFi AP.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "INDRA — Local weather",
        short_name: "INDRA",
        description: "Location readings, parameter maps and weather patterns",
        theme_color: "#1d4938",
        background_color: "#f4f5f0",
        display: "standalone",
        icons: [
          {
            src: "favicon.svg",
            sizes: "any",
            type: "image/svg+xml",
          },
        ],
      },
      workbox: {
        // Cache the app shell aggressively; API calls are handled separately
        // in src/api/client.js with an IndexedDB fallback (see that file).
        globPatterns: ["**/*.{js,css,html,svg}"],
      },
    }),
  ],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8080" },
  },
});
