import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { AuthProvider } from '@/auth/AuthProvider';
import { ServicesProvider } from '@/composition/ServicesProvider';

export default function RootLayout() {
  return (
    <ServicesProvider>
      <AuthProvider>
        <Stack>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="sign-in" options={{ title: 'Sign in', headerShown: false }} />
          <Stack.Screen name="docs" options={{ title: 'Docs' }} />
        </Stack>
        <StatusBar style="auto" />
      </AuthProvider>
    </ServicesProvider>
  );
}
