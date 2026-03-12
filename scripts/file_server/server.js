require('dotenv').config();

const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = Number(process.env.PORT || 29133);
const AUTH_TOKEN = process.env.AUTH_TOKEN || '';
const DOCS_PATH = path.resolve(
  process.env.DOCS_PATH ||
    '/home/bobby/.openclaw/workspace-wecom-dm-hongyu/teaching-docs'
);

const COOKIE_NAME = 'auth_token';

function getCookie(req, name) {
  const raw = req.headers.cookie;
  if (!raw) return null;
  const match = new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)').exec(raw);
  return match ? decodeURIComponent(match[1]) : null;
}

function getToken(req) {
  const header = req.headers.authorization;
  if (header && header.startsWith('Bearer ')) return header.slice(7);
  if (req.query && req.query.token) return req.query.token;
  const cookie = getCookie(req, COOKIE_NAME);
  if (cookie) return cookie;
  return null;
}

function isAuthenticated(req) {
  const token = getToken(req);
  if (!token || !AUTH_TOKEN) return false;
  return token === AUTH_TOKEN;
}

app.use(express.json({ limit: '8kb' }));
app.use(express.urlencoded({ extended: true, limit: '8kb' }));

// Auth middleware for protected routes
function requireAuth(req, res, next) {
  if (isAuthenticated(req)) return next();
  const acceptsHtml =
    req.headers.accept && req.headers.accept.includes('text/html');
  if (acceptsHtml && (req.path === '/' || req.path === '')) {
    return res.status(401).send(getLoginHtml());
  }
  res.status(401).json({ error: 'Unauthorized' });
}

function getLoginHtml() {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Sign in — Teaching Docs</title>
  <link rel="stylesheet" href="/styles.css" />
</head>
<body>
  <main class="app">
    <div class="login-card">
      <h1>Teaching Docs</h1>
      <p class="login-hint">Enter token to continue.</p>
      <form method="post" action="/auth" class="login-form">
        <label for="token">Token</label>
        <input type="password" id="token" name="token" required autocomplete="current-password" />
        <button type="submit">Sign in</button>
      </form>
    </div>
  </main>
</body>
</html>`;
}

// POST /auth — verify token, set cookie, redirect
app.post('/auth', (req, res) => {
  const token =
    (req.body && (req.body.token || req.body.Token)) ||
    (req.query && req.query.token);
  if (!token || !AUTH_TOKEN || token !== AUTH_TOKEN) {
    return res.status(401).send(getLoginHtml());
  }
  res.cookie(COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: 'lax',
    maxAge: 7 * 24 * 60 * 60 * 1000,
    path: '/',
  });
  res.redirect(302, '/');
});

// GET / — serve app or login
app.get('/', requireAuth, (_req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Safe path: must be under DOCS_PATH
function safePath(relativePath) {
  if (!relativePath || relativePath.includes('\0')) return null;
  const normalized = path.normalize(relativePath).replace(/^(\.\.(\/|\\|$))+/, '');
  const absolute = path.resolve(DOCS_PATH, normalized);
  const docsReal = path.resolve(DOCS_PATH);
  if (!absolute.startsWith(docsReal)) return null;
  return absolute;
}

// GET /api/files — list root (optional ?path= for subdir)
app.get('/api/files', requireAuth, (req, res) => {
  const subPath = (req.query.path && String(req.query.path)) || '';
  const dirPath = subPath ? safePath(subPath) : DOCS_PATH;
  if (!dirPath) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  if (!fs.existsSync(dirPath) || !fs.statSync(dirPath).isDirectory()) {
    return res.status(404).json({ error: 'Not found' });
  }
  try {
    const name = path.basename(dirPath) || 'teaching-docs';
    const tree = buildTree(dirPath, subPath || '.');
    res.json({
      name,
      path: subPath || '',
      type: 'directory',
      children: tree,
    });
  } catch (err) {
    res.status(500).json({ error: 'Failed to list directory' });
  }
});

function buildTree(dirPath, basePath) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  const result = [];
  for (const e of entries) {
    const relPath = basePath === '.' ? e.name : path.join(basePath, e.name);
    const fullPath = path.join(dirPath, e.name);
    if (e.isDirectory()) {
      const children = buildTree(fullPath, relPath);
      result.push({
        name: e.name,
        path: relPath,
        type: 'directory',
        children,
      });
    } else {
      result.push({ name: e.name, path: relPath, type: 'file' });
    }
  }
  result.sort((a, b) => {
    if (a.type !== b.type) return a.type === 'directory' ? -1 : 1;
    return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
  });
  return result;
}

// GET /api/files/* — stream file content
app.get(/^\/api\/files\/(.*)$/, requireAuth, (req, res) => {
  const raw = req.params[0] || '';
  const filePath = safePath(raw);
  if (!filePath) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    return res.status(404).json({ error: 'Not found' });
  }
  const ext = path.extname(filePath).toLowerCase();
  const mime =
    {
      '.md': 'text/markdown',
      '.txt': 'text/plain',
      '.json': 'application/json',
      '.html': 'text/html',
      '.css': 'text/css',
      '.js': 'application/javascript',
      '.pdf': 'application/pdf',
    }[ext] || 'application/octet-stream';
  res.setHeader('Content-Type', mime);
  res.sendFile(filePath);
});

// Static assets (CSS, etc.) — after routes so GET / is handled by requireAuth
app.use(express.static(path.join(__dirname, 'public')));

if (!AUTH_TOKEN) {
  console.warn('Warning: AUTH_TOKEN is not set. Set it in .env to enable auth.');
}

app.listen(PORT, () => {
  console.log(`Teaching docs file server listening on http://127.0.0.1:${PORT}`);
  console.log(`Document root: ${DOCS_PATH}`);
});
