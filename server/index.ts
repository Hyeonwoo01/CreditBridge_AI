import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { handleApi } from './api';

try {
  process.loadEnvFile();
} catch {
  // .env가 없으면 환경 변수만 사용
}

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../dist');
const port = Number(process.env.PORT ?? 3000);

const TYPES: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.mjs': 'text/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.json': 'application/json',
  '.png': 'image/png',
};

async function serveStatic(pathname: string): Promise<{ body: Buffer; type: string } | null> {
  const file = path.join(root, path.normalize(pathname).replace(/^(\.\.[/\\])+/, ''));
  if (!file.startsWith(root)) return null;
  try {
    if ((await stat(file)).isFile()) {
      return { body: await readFile(file), type: TYPES[path.extname(file)] ?? 'application/octet-stream' };
    }
  } catch {
    // 파일 없음
  }
  return null;
}

createServer(async (req, res) => {
  const { pathname } = new URL(req.url ?? '/', 'http://localhost');
  if (pathname.startsWith('/api/')) return handleApi(req, res);

  const asset = (await serveStatic(pathname)) ?? (await serveStatic('/index.html'));
  if (!asset) {
    res.statusCode = 404;
    return res.end('Run `npm run build` first.');
  }
  res.setHeader('Content-Type', asset.type);
  res.end(asset.body);
}).listen(port, () => {
  console.log(`CreditBridge running on http://localhost:${port}`);
});
