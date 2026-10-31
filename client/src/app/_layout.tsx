import { Stack, ThemeProvider } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { ServicesProvider } from '@/composition/ServicesProvider';
import { navigationTheme, useAppTheme } from '@/theme/theme';

export default function RootLayout() {
  const theme = useAppTheme();

  return (
    <ThemeProvider value={navigationTheme(theme)}>
      <ServicesProvider>
        <Stack>
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="sign-in" options={{ title: 'Sign in', headerShown: false }} />
          <Stack.Screen name="docs" options={{ title: 'Docs' }} />
          <Stack.Screen name="design" options={{ title: 'Design' }} />
        </Stack>
        <StatusBar style="auto" />
      </ServicesProvider>
    </ThemeProvider>
  );
}
