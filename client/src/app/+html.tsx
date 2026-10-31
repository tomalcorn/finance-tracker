import { ScrollViewStyleReset } from 'expo-router/html';
import type { PropsWithChildren } from 'react';

import { APPLE_TOUCH_ICON_PATH, PWA, startupImageMedia, startupImagePath } from '@/pwa';
import { DARK, LIGHT } from '@/theme/tokens';

const REGISTER_SERVICE_WORKER = `if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js'));
}`;

// iOS has no status-bar style that follows the colour scheme, so it is chosen at launch: in dark
// mode the page draws under the bar (whose text is then white), in light mode the bar is white.
const STATUS_BAR_STYLE = `document.write('<meta name="apple-mobile-web-app-status-bar-style" content="' +
  (matchMedia('(prefers-color-scheme: dark)').matches ? 'black-translucent' : 'default') + '">');`;

const PAGE_BACKGROUND = `body { background-color: ${LIGHT.background}; }
@media (prefers-color-scheme: dark) { body { background-color: ${DARK.background}; } }`;

/**
 * The HTML document around every page of the web build, rendered at export
 * time only. Its head makes the app installable: the manifest, the iOS
 * home-screen tags and start-up images, and, in a production build, the
 * service worker. It also paints the page the theme's background, so
 * overscrolling never shows white.
 */
export default function Root({ children }: PropsWithChildren) {
  return (
    <html lang="en">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1, shrink-to-fit=no, viewport-fit=cover"
        />
        <ScrollViewStyleReset />
        <style dangerouslySetInnerHTML={{ __html: PAGE_BACKGROUND }} />

        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content={PWA.themeColor} />
        <link rel="apple-touch-icon" href={APPLE_TOUCH_ICON_PATH} />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-title" content={PWA.shortName} />
        <script dangerouslySetInnerHTML={{ __html: STATUS_BAR_STYLE }} />
        {PWA.startupImages.map((screen) => (
          <link
            key={startupImagePath(screen)}
            rel="apple-touch-startup-image"
            href={startupImagePath(screen)}
            media={startupImageMedia(screen)}
          />
        ))}

        {process.env.NODE_ENV === 'production' ? (
          <script dangerouslySetInnerHTML={{ __html: REGISTER_SERVICE_WORKER }} />
        ) : null}
      </head>
      <body>{children}</body>
    </html>
  );
}
