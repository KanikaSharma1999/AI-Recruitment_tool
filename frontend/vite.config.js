import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,           // Expose on all network interfaces (0.0.0.0) — allows other devices to connect
    port: 5173,
    allowedHosts: true,  // Disable host validation check for ngrok/dynamic tunnels in Vite 6
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
