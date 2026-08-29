import { createReadStream, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, relative } from 'node:path';

const host = '100.103.134.102';
const port = 19180;
const roots = {
  '/espacio': '/srv/apps/espacio',
  '/restaurante': '/srv/apps/restaurante/dist',
};

const contentTypes = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.woff2': 'font/woff2',
};

function resolveFile(url, referer = '') {
  const pathname = decodeURIComponent(new URL(url, `http://${host}`).pathname);
  const prefix = Object.keys(roots).find((candidate) => pathname === candidate || pathname.startsWith(`${candidate}/`));
  if (!prefix && referer.includes('/restaurante/')) {
    const root = roots['/restaurante'];
    const file = join(root, pathname.replace(/^\/+/, ''));
    const rel = relative(root, normalize(file));
    if (!rel.startsWith('..') && !rel.includes('/..')) {
      try {
        if (statSync(file).isFile()) return file;
      } catch {
        return null;
      }
    }
    return null;
  }
  if (!prefix) return null;

  const root = roots[prefix];
  const suffix = pathname.slice(prefix.length).replace(/^\/+/, '');
  const file = join(root, suffix || 'index.html');
  const rel = relative(root, normalize(file));
  if (rel.startsWith('..') || rel.includes('/..')) return null;

  try {
    const stat = statSync(file);
    if (stat.isDirectory()) return join(file, 'index.html');
    return file;
  } catch {
    return null;
  }
}

const server = createServer((request, response) => {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    response.writeHead(405, { allow: 'GET, HEAD' });
    response.end();
    return;
  }

  const file = resolveFile(request.url, request.headers.referer ?? '');
  if (!file) {
    response.writeHead(404, { 'content-type': 'text/plain; charset=utf-8' });
    response.end('Not found');
    return;
  }

  const type = contentTypes[extname(file)] ?? 'application/octet-stream';
  response.writeHead(200, {
    'cache-control': extname(file) === '.html' ? 'no-cache' : 'public, max-age=3600',
    'content-type': type,
    'x-content-type-options': 'nosniff',
  });
  if (request.method === 'HEAD') response.end();
  else createReadStream(file).pipe(response);
});

server.listen(port, host, () => {
  console.log(`Static sites server listening on http://${host}:${port}`);
});
