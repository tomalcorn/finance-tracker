import type { PressableStateCallbackType } from 'react-native';

import type { Palette } from '@/theme/tokens';

/** A `Pressable`'s state, with the pointer hover that react-native-web adds on the web. */
type InteractionState = PressableStateCallbackType & { hovered?: boolean };

/**
 * The background of a tappable surface: darker while held, a shade off while the pointer is over
 * it, and otherwise `resting`.
 */
export function interactiveBackground(
  state: PressableStateCallbackType,
  colors: Palette,
  resting: string = 'transparent',
): string {
  const { pressed, hovered } = state as InteractionState;
  if (pressed) return colors.surfaceMuted;
  return hovered ? colors.surfaceHover : resting;
}
