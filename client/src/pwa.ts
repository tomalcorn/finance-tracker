import pwa from '@/pwa.json';

/** One iPhone screen size in CSS pixels, with the device pixel ratio that turns it into the image size. */
export type StartupImage = { width: number; height: number; pixelRatio: number };

/** The installed app's name, colours and iOS start-up screens, as set in `src/pwa.json`. */
export const PWA = pwa;

/** Where a start-up image for `screen` is published. */
export function startupImagePath({ width, height, pixelRatio }: StartupImage): string {
  return `/splash/${width * pixelRatio}x${height * pixelRatio}.png`;
}

/** The media query by which iOS picks the start-up image for `screen`, in portrait. */
export function startupImageMedia({ width, height, pixelRatio }: StartupImage): string {
  return (
    `(device-width: ${width}px) and (device-height: ${height}px) and ` +
    `(-webkit-device-pixel-ratio: ${pixelRatio}) and (orientation: portrait)`
  );
}

/** The icons listed by the manifest; each one is offered for both normal and maskable use. */
export const ICON_SIZES = [192, 512] as const;

/** Where the manifest icon of `size` pixels is published. */
export function iconPath(size: number): string {
  return `/icons/icon-${size}.png`;
}

/** Where the iOS home-screen icon is published. */
export const APPLE_TOUCH_ICON_PATH = '/icons/apple-touch-icon.png';
