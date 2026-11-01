import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { interactiveBackground } from '@/components/interaction';
import { ProgressBar } from '@/components/ProgressBar';
import { useAppTheme } from '@/theme/theme';
import { formatAmount } from '@/theme/formatAmount';
import { SPACING } from '@/theme/tokens';

type BudgetRowProps = {
  title: string;
  /** Supporting figures under the title, e.g. "£64 of £120 spent". */
  caption: string;
  /** What is left, shown at the end and flagged once negative. */
  left: number;
  /** Labels `left`, e.g. "left" or "to go". */
  leftLabel?: string;
  /** Percentage used, from the view's `progress`. */
  progress: number;
  /** Draw the bar in the warning colour. */
  warn?: boolean;
  /** It is a goal to reach, like a pot's target, so nothing left means done rather than overspent. */
  goal?: boolean;
  icon?: SymbolViewProps['name'];
  /** The icon's colour; the accent when not given. */
  iconColour?: string;
  onPress?: () => void;
};

/** One budget in a list: its name and figures, what is left, and a bar of how much is used. */
export function BudgetRow({
  title,
  caption,
  left,
  leftLabel = 'left',
  progress,
  warn = false,
  goal = false,
  icon,
  iconColour,
  onPress,
}: BudgetRowProps) {
  const { colors } = useAppTheme();
  const reached = goal && left <= 0;
  const over = !goal && left < 0;
  const status = reached
    ? left < 0
      ? `Saved, ${formatAmount(-left)} extra`
      : 'Saved'
    : over
      ? `${formatAmount(-left)} over`
      : `${formatAmount(left)} ${leftLabel}`;

  return (
    <Pressable
      role={onPress ? 'button' : undefined}
      aria-label={onPress ? title : undefined}
      disabled={!onPress}
      onPress={onPress}
      style={(state) => [
        styles.row,
        { backgroundColor: onPress ? interactiveBackground(state, colors) : 'transparent' },
      ]}
    >
      {icon ? <SymbolView name={icon} size={22} tintColor={iconColour ?? colors.accent} /> : null}
      <View style={styles.body}>
        <View style={styles.line}>
          <AppText numberOfLines={1} style={styles.title}>
            {title}
          </AppText>
          <AppText
            variant="label"
            tone={over ? 'negative' : reached ? 'positive' : 'default'}
            style={styles.amount}
            numberOfLines={1}
          >
            {status}
          </AppText>
        </View>
        <ProgressBar progress={progress / 100} warn={!goal && (warn || over)} />
        <AppText variant="caption" tone="muted" numberOfLines={1}>
          {caption}
        </AppText>
      </View>
      {onPress ? <AppText tone="muted">›</AppText> : null}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
  },
  body: { flex: 1, gap: SPACING.xs },
  line: { flexDirection: 'row', alignItems: 'baseline', gap: SPACING.sm },
  title: { flex: 1 },
  amount: { fontVariant: ['tabular-nums'] },
});
