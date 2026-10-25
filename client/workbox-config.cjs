// Service worker for the web export: precaches the app shell (HTML, JS, CSS,
// fonts, icons) so the installed app opens with no network. Nothing else is
// cached: Supabase and Auth0 are other origins, so their requests always go to
// the network.
module.exports = {
  globDirectory: 'dist',
  globPatterns: ['**/*.{html,js,css,json,png,ico,ttf,woff,woff2}'],
  // iOS fetches start-up images itself when the app is added to the home
  // screen; the `(tabs)` copies of each page are never navigated to.
  globIgnores: ['splash/**', '(tabs)/**'],
  swDest: 'dist/sw.js',
  // `/sign-in?returnTo=…` and Auth0's `/?code=…` callback load the same page as without the query.
  ignoreURLParametersMatching: [/.*/],
  // A new deploy takes over on the next launch, and old caches are cleared.
  skipWaiting: true,
  clientsClaim: true,
  cleanupOutdatedCaches: true,
  maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
};
