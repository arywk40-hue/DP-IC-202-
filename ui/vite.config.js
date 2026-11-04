import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Native PWA plugin: registers the service worker and generates manifest
// without invoking slow external Babel/Workbox child processes on Node 22/macOS.
function pwaPlugin() {
  const virtualModuleId = "virtual:pwa-register";
  const resolvedVirtualModuleId = "\0" + virtualModuleId;
  return {
    name: "indra-pwa-plugin",
    resolveId(id) {
      if (id === virtualModuleId) return resolvedVirtualModuleId;
    },
    load(id) {
      if (id === resolvedVirtualModuleId) {
        return `export function registerSW(options = {}) {
          if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
            window.addEventListener('load', () => {
              navigator.serviceWorker.register('/sw.js').catch((err) => {
                console.warn('PWA service worker registration failed:', err);
              });
            });
          }
        }`;
      }
    },
  };
}

export default defineConfig({
  plugins: [react(), pwaPlugin()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8080" },
  },
});
