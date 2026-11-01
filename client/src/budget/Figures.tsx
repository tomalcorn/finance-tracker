import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { formatAmount } from '@/theme/formatAmount';
import { SPACING } from '@/theme/tokens';

/** A row of headline figures, sharing the width equally. */
export function Figures({ children }: { children: ReactNode }) {
  return <View style={styles.figures}>{children}</View>;
}

type FigureProps = {
  label: string;
  value: number;
  /** Show the amount in the negative colour, e.g. for an overspend. */
  negative?: boolean;
};

/** One headline figure: a small label over an amount. */
export function Figure({ label, value, negative = false }: FigureProps) {
  return (
    <View
      accessible
      aria-label={`${formatAmount(Math.abs(value))} ${label.toLowerCase()}`}
      style={styles.figure}
    >
      <AppText variant="caption" tone="muted">
        {label}
      </AppText>
      <AppText variant="heading" tone={negative ? 'negative' : 'default'} style={styles.amount}>
        {formatAmount(Math.abs(value))}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  figures: { flexDirection: 'row', gap: SPACING.md },
  figure: { flex: 1, gap: 2 },
  amount: { fontVariant: ['tabular-nums'] },
});
