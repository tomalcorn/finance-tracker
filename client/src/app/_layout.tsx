import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

export default function RootLayout() {
  return (
    <>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="docs" options={{ title: 'Docs' }} />
      </Stack>
      <StatusBar style="auto" />
    </>
  );
}
