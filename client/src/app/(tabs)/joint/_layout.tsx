import { Stack } from 'expo-router';

import { HalfThemeProvider } from '@/theme/theme';

/** Keeps the overview beneath a screen opened directly, so Back never leaves the tab. */
export const unstable_settings = { anchor: 'index' };

export default function Layout() {
  return (
    <HalfThemeProvider half="joint">
      <Stack screenOptions={{ headerShown: false }} />
    </HalfThemeProvider>
  );
}
