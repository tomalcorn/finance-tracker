import { renderRouter, screen } from 'expo-router/testing-library';

const APP_DIR = './src/app';

describe('routes', () => {
  it.each([
    ['/', 'Quick Expenses', 295],
    ['/personal', 'Personal', 293],
    ['/joint', 'Joint', 301],
    ['/settings', 'Settings', 302],
    ['/docs', 'Docs', 303],
  ])('%s renders the %s screen', async (url, _title, issue) => {
    await renderRouter(APP_DIR, { initialUrl: url });

    expect(screen.getByText(`Coming in #${issue}.`)).toBeOnTheScreen();
  });
});
