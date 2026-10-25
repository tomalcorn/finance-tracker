import { safeReturnTo } from '@/auth/returnTo';

describe('safeReturnTo', () => {
  it.each(['/', '/personal', '/joint?tab=2'])('keeps the app path %s', (path) => {
    expect(safeReturnTo(path)).toBe(path);
  });

  it.each([
    'https://evil.example',
    'javascript:alert(1)',
    '//evil.example',
    '/\\evil.example',
    'personal',
    '',
    null,
    undefined,
  ])('replaces %p with the home route', (returnTo) => {
    expect(safeReturnTo(returnTo)).toBe('/');
  });
});
