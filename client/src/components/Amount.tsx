import { StyleSheet } from 'react-native';

import { AppText } from '@/components/AppText';
import { formatAmount } from '@/theme/formatAmount';
import type { TextVariant } from '@/theme/tokens';

type AmountProps = {
  value: number;
  variant?: TextVariant;
  /** Colour the amount by its sign: money in green, money out red. */
  signed?: boolean;
};

/** An amount of money in pounds, with digits that line up in a column. */
export function Amount({ value, variant = 'body', signed = false }: AmountProps) {
  const tone = !signed || value === 0 ? 'default' : value > 0 ? 'positive' : 'negative';
  return (
    <AppText variant={variant} tone={tone} style={styles.amount}>
      {formatAmount(value)}
    </AppText>
  );
}

const styles = StyleSheet.create({
  amount: { fontVariant: ['tabular-nums'], fontWeight: '600' },
});
