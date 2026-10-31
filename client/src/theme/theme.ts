import { DarkTheme, DefaultTheme, type Theme as NavigationTheme } from 'expo-router';
import { useColorScheme } from 'react-native';

import { DARK, LIGHT, type Palette } from '@/theme/tokens';

export type AppTheme = {
  dark: boolean;
  colors: Palette;
};

const LIGHT_THEME: AppTheme = { dark: false, colors: LIGHT };
const DARK_THEME: AppTheme = { dark: true, colors: DARK };

/** The theme for the device's current colour scheme. */
export function useAppTheme(): AppTheme {
  return useColorScheme() === 'dark' ? DARK_THEME : LIGHT_THEME;
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
