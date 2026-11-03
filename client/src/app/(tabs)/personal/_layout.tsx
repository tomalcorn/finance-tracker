import { Stack } from 'expo-router';

/** Keeps the overview beneath a screen opened directly, so Back never leaves the tab. */
export const unstable_settings = { anchor: 'index' };

export default function Layout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
