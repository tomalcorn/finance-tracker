import { Stack, ThemeProvider } from 'expo-router';
import { StatusBar } from 'expo-status-bar';

import { ServicesProvider } from '@/composition/ServicesProvider';
import { AppThemeProvider, navigationTheme, useAppTheme } from '@/theme/theme';

export default function RootLayout() {
  return (
    <AppThemeProvider>
      <ThemedRoot />
    </AppThemeProvider>
  );
}

function ThemedRoot() {
  const theme = useAppTheme();

  return (
    <ThemeProvider value={navigationTheme(theme)}>
      <ServicesProvider>
        <Stack screenOptions={{ headerShown: false }}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="sign-in" options={{ title: 'Sign in' }} />
          <Stack.Screen name="docs" options={{ title: 'Docs' }} />
          <Stack.Screen name="design" options={{ title: 'Design' }} />
        </Stack>
        <StatusBar style={theme.dark ? 'light' : 'dark'} />
      </ServicesProvider>
    </ThemeProvider>
  );
}
