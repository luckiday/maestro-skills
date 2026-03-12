require('dotenv').config();

const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = Number(process.env.PORT || 29133);
const AUTH_TOKEN = process.env.AUTH_TOKEN || '';
const DOCS_PATH = path.resolve(
  process.env.DOCS_PATH || '/home/bobby/.openclaw/workspace-wecom-dm-hongyu'
);

// Additional root folders to show in sidebar (label -> path)
const EXTRA_ROOTS = process.env.EXTRA_ROOTS
  ? JSON.parse(process.env.EXTRA_ROOTS)
  : {
      'Skills': '/home/bobby/.agents/skills',
      'Maestro Skills': '/home/bobby/lab/maestro-skills/skills',
    };

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

// GET / — if ?token= valid, set cookie and redirect; else require auth and serve app
app.get('/', (req, res, next) => {
  const token = req.query && req.query.token;
  if (token && AUTH_TOKEN && token === AUTH_TOKEN) {
    res.cookie(COOKIE_NAME, token, {
      httpOnly: true,
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60 * 1000,
      path: '/',
    });
    return res.redirect(302, '/');
  }
  next();
}, requireAuth, (_req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Safe path: must be under DOCS_PATH (follows symlinks)
function safePath(relativePath, allowExternalSymlinks = true) {
  if (!relativePath || relativePath.includes('\0')) return null;
  const normalized = path.normalize(relativePath).replace(/^(\.\.(\/|\\|$))+/, '');
  const absolute = path.resolve(DOCS_PATH, normalized);
  const docsReal = path.resolve(DOCS_PATH);
  if (!absolute.startsWith(docsReal)) return null;
  
  // Follow symlinks to get real path
  let realPath;
  try {
    realPath = fs.realpathSync(absolute);
  } catch {
    realPath = absolute;
  }
  
  // Check if symlink points outside workspace
  const isSymlink = realPath !== absolute;
  if (isSymlink && !allowExternalSymlinks) {
    const realDocs = fs.realpathSync(docsReal);
    if (!realPath.startsWith(realDocs)) return null;
  }
  
  return realPath;
}

// GET /api/roots — list all root folders (workspace + extras with divider)
app.get('/api/roots', requireAuth, (req, res) => {
  const roots = [
    { name: path.basename(DOCS_PATH) || 'Workspace', path: '', type: 'workspace' }
  ];
  
  for (const [label, rootPath] of Object.entries(EXTRA_ROOTS)) {
    if (fs.existsSync(rootPath) && fs.statSync(rootPath).isDirectory()) {
      roots.push({ name: label, path: rootPath, type: 'extra' });
    }
  }
  
  res.json({ roots });
});

// GET /api/extra/:root/* — get file or list directory in extra root (must be before /api/extra/*)
app.get(/^\/api\/extra\/([^/]+)\/(.*)$/, requireAuth, (req, res) => {
  const label = decodeURIComponent(req.params[0]);
  const relPath = req.params[1] || '';
  const rootPath = EXTRA_ROOTS[label];
  
  if (!rootPath) {
    return res.status(404).json({ error: 'Root not found' });
  }
  
  const filePath = path.resolve(rootPath, relPath);
  if (!filePath.startsWith(rootPath)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'Not found' });
  }
  
  const stat = fs.statSync(filePath);
  if (stat.isDirectory()) {
    const children = buildTreeExtra(filePath, relPath);
    return res.json({
      name: path.basename(filePath) || label,
      path: relPath,
      type: 'directory',
      children,
      root: label,
    });
  }
  
  if (!stat.isFile()) {
    return res.status(404).json({ error: 'Not found' });
  }
  
  const ext = path.extname(filePath).toLowerCase();
  const mime = {
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

// GET /api/extra/* — list root of extra (single segment only, e.g. /api/extra/Skills)
app.get(/^\/api\/extra\/([^/]+)$/, requireAuth, (req, res) => {
  const label = decodeURIComponent(req.params[0]);
  const rootPath = EXTRA_ROOTS[label];
  if (!rootPath || !fs.existsSync(rootPath) || !fs.statSync(rootPath).isDirectory()) {
    return res.status(404).json({ error: 'Not found' });
  }
  
  const subPath = req.query.path || '';
  const dirPath = subPath ? path.resolve(rootPath, subPath) : rootPath;
  
  if (!dirPath.startsWith(rootPath)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  
  if (!fs.existsSync(dirPath) || !fs.statSync(dirPath).isDirectory()) {
    return res.status(404).json({ error: 'Not found' });
  }
  
  try {
    const name = path.basename(dirPath) || label;
    const children = buildTreeExtra(dirPath, subPath || '.');
    res.json({
      name,
      path: subPath || '',
      type: 'directory',
      children,
      root: label,
    });
  } catch (err) {
    res.status(500).json({ error: 'Failed to list directory' });
  }
});

function buildTreeExtra(dirPath, basePath) {
  const entries = fs.readdirSync(dirPath, { withFileTypes: true });
  const result = [];
  for (const e of entries) {
    const relPath = basePath === '.' ? e.name : path.join(basePath, e.name);
    const fullPath = path.join(dirPath, e.name);
    if (e.isDirectory()) {
      const children = buildTreeExtra(fullPath, relPath);
      result.push({ name: e.name, path: relPath, type: 'directory', children });
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

// GET /api/files/* — stream file content or list directory
app.get(/^\/api\/files\/(.*)$/, requireAuth, (req, res) => {
  const raw = req.params[0] || '';
  const filePath = safePath(raw);
  if (!filePath) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'Not found' });
  }
  const stat = fs.statSync(filePath);
  
  // If it's a directory, return listing
  if (stat.isDirectory()) {
    try {
      const name = path.basename(filePath) || raw || '/';
      const tree = buildTree(filePath, raw);
      return res.json({
        name,
        path: raw,
        type: 'directory',
        children: tree,
      });
    } catch (err) {
      return res.status(500).json({ error: 'Failed to list directory' });
    }
  }
  
  if (!stat.isFile()) {
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

// DELETE /api/files/* — delete file or directory
app.delete(/^\/api\/files\/(.*)$/, requireAuth, (req, res) => {
  const raw = req.params[0] || '';
  const targetPath = safePath(raw);
  if (!targetPath) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  if (!fs.existsSync(targetPath)) {
    return res.status(404).json({ error: 'Not found' });
  }
  try {
    const stat = fs.statSync(targetPath);
    if (stat.isDirectory()) {
      fs.rmSync(targetPath, { recursive: true });
    } else {
      fs.unlinkSync(targetPath);
    }
    res.json({ success: true, path: raw });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete: ' + err.message });
  }
});

// PUT /api/files/* — create or update file
const EDITABLE_EXTS = ['.md', '.txt', '.json', '.html', '.css', '.js', '.ts', '.yaml', '.yml', '.toml', '.sh'];
app.put(/^\/api\/files\/(.*)$/, requireAuth, (req, res) => {
  const raw = req.params[0] || '';
  const targetPath = safePath(raw);
  if (!targetPath) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  
  const ext = path.extname(targetPath).toLowerCase();
  if (!EDITABLE_EXTS.includes(ext)) {
    return res.status(403).json({ error: 'File type not allowed for editing' });
  }
  
  const dir = path.dirname(targetPath);
  if (!fs.existsSync(dir)) {
    return res.status(404).json({ error: 'Parent directory not found' });
  }
  
  try {
    const content = req.body && (req.body.content || req.body.text);
    if (typeof content !== 'string') {
      return res.status(400).json({ error: 'Missing "content" in request body' });
    }
    fs.writeFileSync(targetPath, content, 'utf8');
    res.json({ success: true, path: raw });
  } catch (err) {
    res.status(500).json({ error: 'Failed to save file: ' + err.message });
  }
});

// Static assets (CSS, etc.) — after routes so GET / is handled by requireAuth
app.use(express.static(path.join(__dirname, 'public')));

// PUT /api/extra/:root/* — update file in extra root
app.put(/^\/api\/extra\/([^/]+)\/(.*)$/, requireAuth, (req, res) => {
  const label = decodeURIComponent(req.params[0]);
  const relPath = req.params[1] || '';
  const rootPath = EXTRA_ROOTS[label];
  
  if (!rootPath) {
    return res.status(404).json({ error: 'Root not found' });
  }
  
  const targetPath = path.resolve(rootPath, relPath);
  if (!targetPath.startsWith(rootPath)) {
    return res.status(400).json({ error: 'Invalid path' });
  }
  
  const ext = path.extname(targetPath).toLowerCase();
  if (!EDITABLE_EXTS.includes(ext)) {
    return res.status(403).json({ error: 'File type not allowed for editing' });
  }
  
  const dir = path.dirname(targetPath);
  if (!fs.existsSync(dir)) {
    return res.status(404).json({ error: 'Parent directory not found' });
  }
  
  try {
    const content = req.body && (req.body.content || req.body.text);
    if (typeof content !== 'string') {
      return res.status(400).json({ error: 'Missing "content" in request body' });
    }
    fs.writeFileSync(targetPath, content, 'utf8');
    res.json({ success: true, path: relPath, root: label });
  } catch (err) {
    res.status(500).json({ error: 'Failed to save file: ' + err.message });
  }
});

if (!AUTH_TOKEN) {
  console.warn('Warning: AUTH_TOKEN is not set. Set it in .env to enable auth.');
}

app.listen(PORT, () => {
  console.log(`Teaching docs file server listening on http://127.0.0.1:${PORT}`);
  console.log(`Document root: ${DOCS_PATH}`);
});
