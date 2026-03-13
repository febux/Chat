import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
      react(),
      {
        name: 'reload',
        configureServer(server) {
          const { ws, watcher } = server
          watcher.on('change', file => {
            if (file.endsWith('.md')) {
              ws.send({
                type: 'full-reload'
              })
            }
          })
        }
      }
  ],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:12000',  // твой FastAPI
        changeOrigin: true,
      },
    },
  },
});
