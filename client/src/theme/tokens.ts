import type { TextStyle } from 'react-native';

/** The colours of one colour scheme, named by role rather than by hue. */
export type Palette = {
  /** The page behind everything. */
  background: string;
  /** Cards, sheets and the tab bar. */
  surface: string;
  /** A recessed area inside a surface: input fields, progress tracks. */
  surfaceMuted: string;
  text: string;
  textMuted: string;
  border: string;
  accent: string;
  /** A tint of the accent, for selected or highlighted areas. */
  accentSoft: string;
  /** Text and icons drawn on the accent. */
  onAccent: string;
  positive: string;
  negative: string;
  warning: string;
};

export const LIGHT: Palette = {
  background: '#F6F5F2',
  surface: '#FFFFFF',
  surfaceMuted: '#EFEDE8',
  text: '#1C1B19',
  textMuted: '#625F59',
  border: '#E2DFD8',
  accent: '#0F766E',
  accentSoft: '#D5ECE8',
  onAccent: '#FFFFFF',
  positive: '#15803D',
  negative: '#B42318',
  warning: '#A15C07',
};

export const DARK: Palette = {
  background: '#111413',
  surface: '#1B1F1E',
  surfaceMuted: '#262B2A',
  text: '#ECEDEB',
  textMuted: '#A0A7A4',
  border: '#2F3534',
  accent: '#5EC4B6',
  accentSoft: '#163C38',
  onAccent: '#0B1F1D',
  positive: '#5BD48A',
  negative: '#F2877D',
  warning: '#F2B455',
};

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const RADIUS = {
  sm: 8,
  md: 12,
  lg: 16,
  pill: 999,
} as const;

export type TextVariant = 'title' | 'heading' | 'body' | 'label' | 'caption';

export const TYPOGRAPHY: Record<TextVariant, TextStyle> = {
  title: { fontSize: 28, lineHeight: 34, fontWeight: '700', letterSpacing: -0.4 },
  heading: { fontSize: 20, lineHeight: 26, fontWeight: '600', letterSpacing: -0.2 },
  body: { fontSize: 16, lineHeight: 22, fontWeight: '400' },
  label: { fontSize: 14, lineHeight: 20, fontWeight: '500' },
  caption: { fontSize: 13, lineHeight: 18, fontWeight: '400' },
};

/** The widest a screen's content column grows on a desktop window. */
export const MAX_CONTENT_WIDTH = 640;
