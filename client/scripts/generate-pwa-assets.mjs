// Generate the installed app's icons, iOS start-up images and web manifest
// from `src/pwa.json`. Run with `npm run pwa:assets` after changing it, and
// commit the output: the build does not run this.
import { Resvg } from '@resvg/resvg-js';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const pwa = JSON.parse(readFileSync(new URL('../src/pwa.json', import.meta.url), 'utf8'));
const publicDir = new URL('../public/', import.meta.url);

/**
 * A rising line chart, with a fill that fades out beneath it, drawn in a 100-unit square. The same
 * shape as `components/AppIcon.tsx`, from the same `mark` settings.
 */
function mark() {
  const { color, chart, floor, lineWidth, dotRadius, fillOpacity } = pwa.mark;
  const points = chart.map(([x, y]) => `${x} ${y}`).join(' L');
  const [[firstX], [lastX, lastY]] = [chart[0], chart.at(-1)];
  return `<defs>
    <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${color}" stop-opacity="${fillOpacity}"/>
      <stop offset="1" stop-color="${color}" stop-opacity="0"/>
    </linearGradient>
  </defs>
  <path d="M${points} V${floor} H${firstX} Z" fill="url(#fade)"/>
  <path d="M${points}" fill="none" stroke="${color}" stroke-width="${lineWidth}"
    stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="${lastX}" cy="${lastY}" r="${dotRadius}" fill="${color}"/>`;
}

/** The mark, `markSize` pixels square, centred on the background colour, as a PNG of `width` × `height`. */
function render(width, height, markSize) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
  <rect width="100%" height="100%" fill="${pwa.backgroundColor}"/>
  <g transform="translate(${(width - markSize) / 2} ${(height - markSize) / 2}) scale(${markSize / 100})">
  ${mark()}
  </g>
</svg>`;
  return new Resvg(svg).render().asPng();
}

function write(path, contents) {
  const url = new URL(path, publicDir);
  mkdirSync(new URL('.', url), { recursive: true });
  writeFileSync(url, contents);
}

// Drawn a little smaller, the end dot stays inside the circle a maskable icon may be cut to (80% of its width).
for (const size of [192, 512]) {
  write(`icons/icon-${size}.png`, render(size, size, size * 0.92));
}
write('icons/apple-touch-icon.png', render(180, 180, 180));
writeFileSync(new URL('../assets/favicon.png', import.meta.url), render(48, 48, 48));

for (const { width, height, pixelRatio } of pwa.startupImages) {
  const [w, h] = [width * pixelRatio, height * pixelRatio];
  write(`splash/${w}x${h}.png`, render(w, h, w * 0.4));
}

const icons = [192, 512].flatMap((size) =>
  ['any', 'maskable'].map((purpose) => ({
    src: `/icons/icon-${size}.png`,
    sizes: `${size}x${size}`,
    type: 'image/png',
    purpose,
  })),
);
const manifest = {
  name: pwa.name,
  short_name: pwa.shortName,
  start_url: '/',
  scope: '/',
  display: 'standalone',
  orientation: 'portrait',
  theme_color: pwa.themeColor,
  background_color: pwa.backgroundColor,
  icons,
};
write('manifest.json', `${JSON.stringify(manifest, null, 2)}\n`);
