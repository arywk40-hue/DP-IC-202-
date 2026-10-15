import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

// This config packages the dashboard as an installable, offline-first PWA —
// per the project's design requirement that the admin device works even
// when disconnected from the Master Node's WiFi AP.
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'Mesh Micro-Climate Dashboard',
        short_name: 'MeshDash',
        description: 'Admin dashboard for the Hybrid Mesh Micro-Climate WSN',
        theme_color: '#0b1220',
        background_color: '#0b1220',
        display: 'standalone',
        icons: [
          {
            src: 'favicon.svg',
            sizes: 'any',
            type: 'image/svg+xml'
          }
        ]
      },
      workbox: {
        // Cache the app shell aggressively; API calls are handled separately
        // in src/api/client.js with an IndexedDB fallback (see that file).
        globPatterns: ['**/*.{js,css,html,svg}']
      }
    })
  ],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: { '/api': 'http://127.0.0.1:8080' }
  }
});
