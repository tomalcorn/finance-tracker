import { renderToStaticMarkup } from 'react-dom/server';

import Root from '@/app/+html';
import { PWA } from '@/pwa';
import { DARK } from '@/theme/tokens';

const ORIGINAL_NODE_ENV = process.env.NODE_ENV;

function renderHead(nodeEnv: 'development' | 'production'): string {
  process.env.NODE_ENV = nodeEnv;
  return renderToStaticMarkup(<Root />);
}

afterEach(() => {
  process.env.NODE_ENV = ORIGINAL_NODE_ENV;
});

describe('the HTML head', () => {
  it('links the manifest', () => {
    expect(renderHead('production')).toContain('<link rel="manifest" href="/manifest.json"/>');
  });

  it('lets the page reach under the iPhone safe areas, so their insets are reported', () => {
    expect(renderHead('production')).toMatch(/name="viewport" content="[^"]*viewport-fit=cover/);
  });

  it('draws under the iOS status bar in dark mode, so it is not white', () => {
    expect(renderHead('production')).toContain("'black-translucent' : 'default'");
  });

  it('paints the page the dark background in dark mode', () => {
    expect(renderHead('production')).toContain(`background-color: ${DARK.background}`);
  });

  it('sets the theme colour', () => {
    expect(renderHead('production')).toContain(
      `<meta name="theme-color" content="${PWA.themeColor}"/>`,
    );
  });

  it('offers a start-up image for every iPhone screen size', () => {
    const links = renderHead('production').match(/rel="apple-touch-startup-image"/g) ?? [];

    expect(links).toHaveLength(PWA.startupImages.length);
  });

  it('registers the service worker in a production build', () => {
    expect(renderHead('production')).toContain("navigator.serviceWorker.register('/sw.js')");
  });

  it('leaves the service worker out of development, where there is none', () => {
    expect(renderHead('development')).not.toContain('serviceWorker');
  });
});
