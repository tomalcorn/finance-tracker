/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import {
  APPLE_TOUCH_ICON_PATH,
  ICON_SIZES,
  iconPath,
  PWA,
  startupImageMedia,
  startupImagePath,
} from '@/pwa';

const PUBLIC_DIR = join(__dirname, '..', '..', 'public');

type ManifestIcon = { src: string; sizes: string; purpose: string };
const manifest = JSON.parse(readFileSync(join(PUBLIC_DIR, 'manifest.json'), 'utf8'));

/** The width × height in a PNG's header, of the file published at `path`. */
function pngSize(path: string): string {
  const header = readFileSync(join(PUBLIC_DIR, path)).subarray(16, 24);
  return `${header.readUInt32BE(0)}x${header.readUInt32BE(4)}`;
}

describe('manifest', () => {
  it('matches src/pwa.json', () => {
    expect(manifest).toMatchObject({
      name: PWA.name,
      short_name: PWA.shortName,
      theme_color: PWA.themeColor,
      background_color: PWA.backgroundColor,
      display: 'standalone',
      start_url: '/',
    });
  });

  it('offers every icon size for both normal and maskable use', () => {
    const offered = manifest.icons.map((icon: ManifestIcon) => `${icon.src} ${icon.purpose}`);

    expect(offered).toEqual(
      ICON_SIZES.flatMap((size) => [`${iconPath(size)} any`, `${iconPath(size)} maskable`]),
    );
  });

  it.each(ICON_SIZES)('publishes the %i px icon at that size', (size) => {
    expect(pngSize(iconPath(size))).toBe(`${size}x${size}`);
  });
});

describe('iOS', () => {
  it('publishes the home-screen icon at 180 px', () => {
    expect(pngSize(APPLE_TOUCH_ICON_PATH)).toBe('180x180');
  });

  it.each(PWA.startupImages)(
    'publishes the start-up image for a $width × $height @$pixelRatio screen at full resolution',
    (screen) => {
      expect(pngSize(startupImagePath(screen))).toBe(
        `${screen.width * screen.pixelRatio}x${screen.height * screen.pixelRatio}`,
      );
    },
  );

  it('selects a start-up image by the screen it was made for', () => {
    expect(startupImageMedia({ width: 393, height: 852, pixelRatio: 3 })).toBe(
      '(device-width: 393px) and (device-height: 852px) and ' +
        '(-webkit-device-pixel-ratio: 3) and (orientation: portrait)',
    );
  });
});
