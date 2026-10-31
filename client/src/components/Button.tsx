import { Pressable, StyleSheet } from 'react-native';

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

/** A tappable button in one of the theme's styles. */
export function Button({ title, onPress, variant = 'primary', disabled = false }: ButtonProps) {
  const { colors } = useAppTheme();
  const { fill, text } = VARIANT_COLOURS[variant];

  return (
    <Pressable
      role="button"
      onPress={onPress}
      disabled={disabled}
      aria-disabled={disabled}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: fill ? colors[fill] : 'transparent' },
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      <AppText style={[TYPOGRAPHY.label, styles.title, { color: colors[text] }]}>{title}</AppText>
    </Pressable>
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
  pressed: { opacity: 0.7 },
  disabled: { opacity: 0.4 },
});
