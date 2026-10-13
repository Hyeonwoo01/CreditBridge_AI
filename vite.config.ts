import { defineConfig, loadEnv, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import { handleApi } from './server/api';

/** 개발 서버에서 /api/* 를 같은 프로세스로 처리한다. */
function apiPlugin(): Plugin {
  return {
    name: 'creditbridge-api',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url?.startsWith('/api/')) return next();
        void handleApi(req, res);
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  // .env의 ANTHROPIC_API_KEY를 서버 코드(process.env)에서 읽을 수 있게 한다.
  for (const [k, v] of Object.entries(loadEnv(mode, process.cwd(), 'ANTHROPIC_'))) process.env[k] ??= v;
  return { plugins: [react(), apiPlugin()] };
});
