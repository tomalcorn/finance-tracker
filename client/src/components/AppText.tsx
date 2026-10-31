import { Text, type TextProps } from 'react-native';

import { useAppTheme } from '@/theme/theme';
import { TYPOGRAPHY, type Palette, type TextVariant } from '@/theme/tokens';

type Tone = 'default' | 'muted' | 'accent' | 'positive' | 'negative';

type AppTextProps = TextProps & {
  variant?: TextVariant;
  tone?: Tone;
};

const TONE_COLOUR: Record<Tone, keyof Palette> = {
  default: 'text',
  muted: 'textMuted',
  accent: 'accent',
  positive: 'positive',
  negative: 'negative',
};

/** Text in one of the theme's type styles and colours. */
export function AppText({ variant = 'body', tone = 'default', style, ...props }: AppTextProps) {
  const { colors } = useAppTheme();
  return (
    <Text
      role={variant === 'title' || variant === 'heading' ? 'heading' : undefined}
      style={[TYPOGRAPHY[variant], { color: colors[TONE_COLOUR[tone]] }, style]}
      {...props}
    />
  );
}
