import { useRef, useState } from 'react';
import { Animated, Platform, Pressable, StyleSheet } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import type { Palette } from '@/theme/tokens';
import { RADIUS, SPACING, TYPOGRAPHY } from '@/theme/tokens';

type ButtonVariant = 'primary' | 'secondary' | 'plain' | 'destructive';

type ButtonProps = {
  title: string;
  onPress: () => void;
  variant?: ButtonVariant;
  disabled?: boolean;
};

const VARIANT_COLOURS: Record<ButtonVariant, { fill: keyof Palette | null; text: keyof Palette }> =
  {
    primary: { fill: 'accent', text: 'onAccent' },
    secondary: { fill: 'accentSoft', text: 'accent' },
    plain: { fill: null, text: 'accent' },
    destructive: { fill: null, text: 'negative' },
  };

const USE_NATIVE_DRIVER = Platform.OS !== 'web';

/** How far a held button shrinks, and how much it dims at the bottom. */
const PRESSED_SCALE = 0.965;
const PRESSED_OPACITY = 0.9;
const DISABLED_OPACITY = 0.4;

/** The shortest time a tap holds the button down, so even a quick one visibly lands. */
const MIN_PRESS_MS = 60;

const PRESS = { stiffness: 900, damping: 48, mass: 1, useNativeDriver: USE_NATIVE_DRIVER };
/** Underdamped, so the button re-expands a little past full size before settling. */
const RELEASE = { stiffness: 480, damping: 19, mass: 1, useNativeDriver: USE_NATIVE_DRIVER };

/** A tappable button in one of the theme's styles, which shrinks under the finger and springs back. */
export function Button({ title, onPress, variant = 'primary', disabled = false }: ButtonProps) {
  const { colors } = useAppTheme();
  const { fill, text } = VARIANT_COLOURS[variant];
  const [scale] = useState(() => new Animated.Value(1));
  const pressedAt = useRef(0);

  function pressIn() {
    pressedAt.current = Date.now();
    Animated.spring(scale, { toValue: PRESSED_SCALE, ...PRESS }).start();
  }

  function pressOut() {
    const release = Animated.spring(scale, { toValue: 1, ...RELEASE });
    const held = Date.now() - pressedAt.current;
    if (held >= MIN_PRESS_MS) {
      release.start();
      return;
    }
    Animated.sequence([Animated.delay(MIN_PRESS_MS - held), release]).start();
  }

  return (
    <Animated.View
      style={{
        transform: [{ scale }],
        opacity: disabled
          ? DISABLED_OPACITY
          : scale.interpolate({
              inputRange: [PRESSED_SCALE, 1],
              outputRange: [PRESSED_OPACITY, 1],
              extrapolate: 'clamp',
            }),
      }}
    >
      <Pressable
        role="button"
        onPress={onPress}
        onPressIn={pressIn}
        onPressOut={pressOut}
        disabled={disabled}
        aria-disabled={disabled}
        style={[styles.button, { backgroundColor: fill ? colors[fill] : 'transparent' }]}
      >
        <AppText style={[TYPOGRAPHY.label, styles.title, { color: colors[text] }]}>{title}</AppText>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  button: {
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: SPACING.lg,
    borderRadius: RADIUS.md,
  },
  title: { fontSize: 16, fontWeight: '600' },
});
