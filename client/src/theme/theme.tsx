import { DarkTheme, DefaultTheme, type Theme as NavigationTheme } from 'expo-router';
import { createContext, useContext, useSyncExternalStore, type ReactNode } from 'react';
import { useColorScheme } from 'react-native';

import { DARK, LIGHT, type Palette } from '@/theme/tokens';

export type AppTheme = {
  dark: boolean;
  colors: Palette;
};

const LIGHT_THEME: AppTheme = { dark: false, colors: LIGHT };
const DARK_THEME: AppTheme = { dark: true, colors: DARK };

const AppThemeContext = createContext<AppTheme>(LIGHT_THEME);

const noSubscription = () => () => {};

/**
 * Whether this render runs after hydration. The web export pre-renders every page in the light
 * theme, and hydration keeps the pre-rendered styles, so the first client render must match them;
 * the device's scheme takes over on the render after.
 */
function useHydrated(): boolean {
  return useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
}

/** Provide the theme for the device's colour scheme, following it as it changes. */
export function AppThemeProvider({ children }: { children: ReactNode }) {
  const scheme = useColorScheme();
  const hydrated = useHydrated();
  const theme = hydrated && scheme === 'dark' ? DARK_THEME : LIGHT_THEME;
  return <AppThemeContext.Provider value={theme}>{children}</AppThemeContext.Provider>;
}

/** The current theme: the light one outside an `AppThemeProvider`. */
export function useAppTheme(): AppTheme {
  return useContext(AppThemeContext);
}

/** The navigation theme matching an app theme, for headers and the tab bar. */
export function navigationTheme({ dark, colors }: AppTheme): NavigationTheme {
  const base = dark ? DarkTheme : DefaultTheme;
  return {
    ...base,
    colors: {
      primary: colors.accent,
      background: colors.background,
      card: colors.surface,
      text: colors.text,
      border: colors.border,
      notification: colors.negative,
    },
  };
}
