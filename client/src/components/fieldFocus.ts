import { useState } from 'react';
import { Platform } from 'react-native';

import type { Palette } from '@/theme/tokens';

/**
 * Turns off the browser's own focus ring, for a field that shows focus with `fieldBorderColor`
 * instead. A plain object, since React Native's style types don't allow `outlineStyle: 'none'`.
 */
export const NO_FOCUS_RING: object = Platform.select({
  web: { outlineStyle: 'none' },
  default: {},
});

/** A field's border: the negative colour for an error, else the accent while focused, else none. */
export function fieldBorderColor(
  colors: Pick<Palette, 'accent' | 'negative'>,
  { error, focused }: { error?: string; focused: boolean },
): string {
  if (error) return colors.negative;
  return focused ? colors.accent : 'transparent';
}

type FocusHandlers<E> = { onFocus?: (event: E) => void; onBlur?: (event: E) => void };

/**
 * Whether a field has focus, and the `onFocus`/`onBlur` handlers that track it. Any handlers passed
 * in still run.
 */
export function useFieldFocus<E>({ onFocus, onBlur }: FocusHandlers<E> = {}) {
  const [focused, setFocused] = useState(false);
  return {
    focused,
    focusHandlers: {
      onFocus: (event: E) => {
        setFocused(true);
        onFocus?.(event);
      },
      onBlur: (event: E) => {
        setFocused(false);
        onBlur?.(event);
      },
    },
  };
}
