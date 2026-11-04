import { Stack } from 'expo-router';

/** Keeps the list beneath a guide opened directly, so Back goes to it. */
export const unstable_settings = { anchor: 'index' };

export default function Layout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
