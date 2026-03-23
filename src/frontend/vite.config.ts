import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from "path"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_');

  const backendUrl = env.VITE_BACKEND_URL || 'http://localhost:8080';
  const serverPort = Number(env.VITE_PORT) || 3000;

  return {
    plugins: [
      react(),
      {
        name: 'reload',
        configureServer(server) {
          const { ws, watcher } = server;
          watcher.on('change', file => {
            if (file.endsWith('.md')) {
              ws.send({ type: 'full-reload' });
            }
          });
        },
      },
    ],
    server: {
      host: '0.0.0.0',
      port: serverPort,
      proxy: {
        '/api': {
          target: backendUrl,
          changeOrigin: true,
        },
      },
    },
    build: {
      rollupOptions: {},
      commonjsOptions: {
        include: [/node_modules/],
      },
    },
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
      dedupe: ['react', 'react-dom', 'prop-types'],
    },
    optimizeDeps: {
      include: ['react', 'react-dom', 'prop-types'],
    },
  };
});