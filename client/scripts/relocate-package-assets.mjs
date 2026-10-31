// Move the assets the web export copies from packages out of
// `dist/assets/node_modules`, and point the bundle at their new home.
// Cloudflare Pages never uploads a folder named `node_modules`, so without
// this every package asset (the icon font, expo-router's images) 404s once
// deployed. Run after `expo export` and before the service worker is built,
// so it precaches the new paths.
import { existsSync, readdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const DIST = new URL('../dist/', import.meta.url).pathname;
const FROM = 'assets/node_modules';
const TO = 'assets/packages';
const REWRITTEN = /\.(js|html|css|json)$/;

if (existsSync(join(DIST, FROM))) {
  renameSync(join(DIST, FROM), join(DIST, TO));
}

let files = 0;
for (const entry of readdirSync(DIST, { recursive: true, withFileTypes: true })) {
  if (!entry.isFile() || !REWRITTEN.test(entry.name)) continue;
  const path = join(entry.parentPath, entry.name);
  const text = readFileSync(path, 'utf8');
  if (!text.includes(`/${FROM}/`)) continue;
  writeFileSync(path, text.replaceAll(`/${FROM}/`, `/${TO}/`));
  files += 1;
}
console.log(`Moved package assets to dist/${TO}, rewriting ${files} file(s).`);
