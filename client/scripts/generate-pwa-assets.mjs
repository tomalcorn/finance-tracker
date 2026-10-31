// Generate the installed app's icons, iOS start-up images and web manifest
// from `src/pwa.json`. Run with `npm run pwa:assets` after changing it, and
// commit the output: the build does not run this.
import { Resvg } from '@resvg/resvg-js';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';

const pwa = JSON.parse(readFileSync(new URL('../src/pwa.json', import.meta.url), 'utf8'));
const publicDir = new URL('../public/', import.meta.url);

// The `currency_pound` glyph from Material Symbols (Bold, Apache-2.0), in its 960-unit em with y up.
const POUND = `M215 86V204Q232 212 251 225Q270 238 286 256.5Q302 275 312.5 298.5Q323 322 323 349Q323 356
322.5 364Q322 372 320 377H215V503H256Q240 532 227.5 567Q215 602 215 651Q215 753 285.5 823.5Q356 894
458 894Q546 894 609 846.5Q672 799 701 718L584 669Q570 715 536.5 741.5Q503 768 458 768Q409 768 375
734.5Q341 701 341 651Q341 606 358 573.5Q375 541 402 503H581V377H446Q447 372 448 364Q449 356 449
349Q449 309 437 274Q425 239 402 212H558Q588 212 605.5 231Q623 250 629 286L745 242Q730 171 677
128.5Q624 86 558 86Z`;
const POUND_BOUNDS = { x: [215, 745], y: [86, 894] };

const RING_RADIUS = 30;
const RING_WIDTH = 5;
const RING_FILLED = 0.7;
const POUND_HEIGHT = 26;
// A £ is heavy at the foot and open at the top, so it reads as centred a little above the middle.
const POUND_RAISE = 3;

/** A budget ring around a £, drawn in a 100-unit square. */
function mark() {
  const circumference = 2 * Math.PI * RING_RADIUS;
  const scale = POUND_HEIGHT / (POUND_BOUNDS.y[1] - POUND_BOUNDS.y[0]);
  const glyphX = (POUND_BOUNDS.x[0] + POUND_BOUNDS.x[1]) / 2;
  const glyphY = (POUND_BOUNDS.y[0] + POUND_BOUNDS.y[1]) / 2;
  const ring = `cx="50" cy="50" r="${RING_RADIUS}" fill="none" stroke="${pwa.mark.color}"
    stroke-width="${RING_WIDTH}"`;
  return `<circle ${ring} stroke-opacity="0.25"/>
  <circle ${ring} stroke-linecap="round" transform="rotate(-90 50 50)"
    stroke-dasharray="${circumference * RING_FILLED} ${circumference}"/>
  <path d="${POUND}" fill="${pwa.mark.color}" transform="translate(50 ${50 - POUND_RAISE})
    scale(${scale} ${-scale}) translate(${-glyphX} ${-glyphY})"/>`;
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

// The ring's outer edge sits inside the circle a maskable icon may be cut to (80% of its width).
for (const size of [192, 512]) {
  write(`icons/icon-${size}.png`, render(size, size, size));
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
