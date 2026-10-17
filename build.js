import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('[R5 Build] Preparing static assets for production deployment...');

const frontendDir = path.join(__dirname, 'frontend');
const rootIndex = path.join(__dirname, 'index.html');
const frontendIndex = path.join(frontendDir, 'index.html');
const frontendRedirects = path.join(frontendDir, '_redirects');
const rootRedirects = path.join(__dirname, '_redirects');

// 1. Ensure _redirects exists in frontend/
const redirectsContent = '/*    /index.html   200\n';
fs.writeFileSync(frontendRedirects, redirectsContent, 'utf-8');
fs.writeFileSync(rootRedirects, redirectsContent, 'utf-8');
console.log('[R5 Build] ✓ Created frontend/_redirects and root _redirects');

// 2. Sync index.html to root as dual-deployment fallback
if (fs.existsSync(frontendIndex)) {
  fs.copyFileSync(frontendIndex, rootIndex);
  console.log('[R5 Build] ✓ Synced frontend/index.html to root index.html');
}

// 3. Mirror static/ to root static/ for zero-config fallback
const frontendStatic = path.join(frontendDir, 'static');
const rootStatic = path.join(__dirname, 'static');

function copyDirRecursive(src, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }
  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

if (fs.existsSync(frontendStatic)) {
  copyDirRecursive(frontendStatic, rootStatic);
  console.log('[R5 Build] ✓ Mirrored static assets to root static/ directory');
}

console.log('[R5 Build] Deployment preparation complete.');
