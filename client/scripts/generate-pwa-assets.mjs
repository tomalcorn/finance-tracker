// Generate the installed app's icons, iOS start-up images and web manifest
// from `src/pwa.json`. Run with `npm run pwa:assets` after changing it, and
// commit the output: the build does not run this.
import { Resvg } from '@resvg/resvg-js';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const pwa = JSON.parse(readFileSync(new URL('../src/pwa.json', import.meta.url), 'utf8'));
const publicDir = new URL('../public/', import.meta.url);

/** The mark centred on the background colour, as a PNG of `width` × `height`. */
function render(width, height, markSize) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
  <rect width="100%" height="100%" fill="${pwa.backgroundColor}"/>
  <text x="50%" y="50%" text-anchor="middle" dominant-baseline="central"
    font-family="Helvetica Neue, Helvetica, Arial, sans-serif" font-weight="700"
    font-size="${markSize}" fill="${pwa.mark.color}">${pwa.mark.text}</text>
</svg>`;
  return new Resvg(svg, { font: { loadSystemFonts: true } }).render().asPng();
}

function write(path, contents) {
  const url = new URL(path, publicDir);
  mkdirSync(new URL('.', url), { recursive: true });
  writeFileSync(url, contents);
}

// Half the icon's width keeps the mark inside the circle a maskable icon may be cut to.
for (const size of [192, 512]) {
  write(`icons/icon-${size}.png`, render(size, size, size * 0.5));
}
write('icons/apple-touch-icon.png', render(180, 180, 90));
writeFileSync(new URL('../assets/favicon.png', import.meta.url), render(48, 48, 30));

for (const { width, height, pixelRatio } of pwa.startupImages) {
  const [w, h] = [width * pixelRatio, height * pixelRatio];
  write(`splash/${w}x${h}.png`, render(w, h, w * 0.2));
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
