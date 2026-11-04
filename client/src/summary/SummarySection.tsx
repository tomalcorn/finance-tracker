import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { Card, CardHeading } from '@/components/Card';
import { SparkBars } from '@/components/SparkBars';
import { Sparkline } from '@/components/Sparkline';
import { today, type OwnershipType } from '@/domain/entities';
import { useRepositories, useRows } from '@/hooks/repositories';
import {
  describeBudget,
  describeSpentChange,
  HISTORY_MONTHS,
  spentChange,
  summarise,
  type FinanceSummary,
} from '@/summary/financeSummary';
import { formatAmount } from '@/theme/formatAmount';
import { SPACING } from '@/theme/tokens';

type SummarySectionProps = { ownership: OwnershipType };

/** One half's headline figures, loaded from its accounts, categories and payments. */
export function SummarySection({ ownership }: SummarySectionProps) {
  const repositories = useRepositories();
  const accounts = useRows(repositories.bankAccounts(ownership));
  const categories = useRows(repositories.categories(ownership));
  const payments = useRows(repositories.payments(ownership));

  const error = accounts.error ?? categories.error ?? payments.error;
  if (error) {
    return <AppText tone="negative">Could not load your summary: {error.message}</AppText>;
  }
  if (!accounts.data || !categories.data || !payments.data) {
    return <AppText tone="muted">Loading…</AppText>;
  }
  return (
    <SummaryTiles summary={summarise(accounts.data, categories.data, payments.data, today())} />
  );
}

type TileProps = {
  label: string;
  value: number;
  caption?: ReactNode;
  chart?: ReactNode;
  /** Stretch to match a tile beside it. */
  fill?: boolean;
};

function Tile({ label, value, caption, chart, fill = false }: TileProps) {
  return (
    <Card fill={fill}>
      <View style={styles.figures}>
        <AppText variant="label" tone="muted" numberOfLines={1}>
          {label}
        </AppText>
        <Amount value={value} variant="heading" />
        {caption}
      </View>
      {chart}
    </Card>
  );
}

/**
 * The total balance with its history, then what is left of the budget beside what was spent this
 * month. More spending than last month is the bad direction.
 */
export function SummaryTiles({ summary }: { summary: FinanceSummary }) {
  const change = describeSpentChange(summary);

  return (
    <View style={styles.section}>
      <CardHeading title="Summary" />
      <Tile
        label="Total balance"
        value={summary.totalBalance}
        chart={<Sparkline values={summary.balanceHistory} area />}
      />
      <View style={styles.row}>
        <View style={styles.cell}>
          <Tile
            fill
            label="Remaining budget"
            value={summary.remainingBudget}
            caption={
              <AppText variant="caption" tone="muted">
                {describeBudget(summary)}
              </AppText>
            }
          />
        </View>
        <View style={styles.cell}>
          <Tile
            fill
            label="Spent this month"
            value={summary.spent}
            caption={
              change ? (
                <AppText
                  variant="caption"
                  tone={spentChange(summary) > 0 ? 'negative' : 'positive'}
                >
                  {change}
                </AppText>
              ) : null
            }
            chart={
              <SparkBars
                values={summary.spentHistory}
                label={`Spending by month for the last ${HISTORY_MONTHS} months: ${summary.spentHistory.map(formatAmount).join(', ')}`}
              />
            }
          />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: SPACING.sm },
  figures: { gap: SPACING.xs },
  row: { flexDirection: 'row', gap: SPACING.md },
  cell: { flex: 1, minWidth: 0 },
});
