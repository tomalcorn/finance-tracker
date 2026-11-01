import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import type { CategoryView } from '@/domain/readModels';
import { useAppTheme } from '@/theme/theme';
import { formatAmount } from '@/theme/formatAmount';
import { RADIUS, SPACING } from '@/theme/tokens';

/** Each tracker's colour, the same as on the Streamlit allocation ring. */
const TRACKER_COLOURS: Record<'light' | 'dark', Record<string, string>> = {
  light: { Expenses: '#2a78d6', Joint: '#eb6834', 'One-offs': '#1baf7a', Savings: '#eda100' },
  dark: { Expenses: '#3987e5', Joint: '#d95926', 'One-offs': '#199e70', Savings: '#c98500' },
};

const UNALLOCATED = { light: '#8a897f', dark: '#7a7972' };

/** The colour that stands for a tracker, wherever its share of income is drawn. */
export function useTrackerColour(): (name: string) => string {
  const { dark } = useAppTheme();
  const scheme = dark ? 'dark' : 'light';
  return (name) => TRACKER_COLOURS[scheme][name] ?? UNALLOCATED[scheme];
}

type AllocationBarProps = {
  trackers: readonly CategoryView[];
  income: number;
};

/**
 * Income split between the trackers: one bar, a segment per tracker’s budget from the largest down,
 * then what is left unallocated. Once the budgets add up to more than the income, the bar is scaled
 * to the budgets and the overspend is called out.
 */
export function AllocationBar({ trackers, income }: AllocationBarProps) {
  const { colors, dark } = useAppTheme();
  const colourOf = useTrackerColour();
  const allocated = trackers.reduce((total, tracker) => total + tracker.budget, 0);
  const left = income - allocated;
  const whole = Math.max(income, allocated);
  const largestFirst = [...trackers].sort((a, b) => b.budget - a.budget);
  const unallocatedColour = UNALLOCATED[dark ? 'dark' : 'light'];
  const segments = [
    ...largestFirst.map((tracker) => ({
      key: tracker.id,
      value: tracker.budget,
      colour: colourOf(tracker.name),
    })),
    { key: 'unallocated', value: Math.max(left, 0), colour: unallocatedColour },
  ].filter((segment) => segment.value > 0);

  return (
    <View style={styles.allocation}>
      <View
        accessible
        role="img"
        aria-label={`${formatAmount(allocated)} of ${formatAmount(income)} income allocated`}
        style={[styles.bar, { backgroundColor: colors.surfaceMuted }]}
      >
        {whole > 0
          ? segments.map((segment) => (
              <View
                key={segment.key}
                style={[
                  styles.segment,
                  { flex: segment.value / whole, backgroundColor: segment.colour },
                ]}
              />
            ))
          : null}
      </View>
      <View style={styles.legend}>
        {largestFirst.map((tracker) => (
          <LegendKey
            key={tracker.id}
            colour={colourOf(tracker.name)}
            label={`${tracker.name} ${formatAmount(tracker.budget)}`}
          />
        ))}
        {left > 0 ? (
          <LegendKey colour={unallocatedColour} label={`Unallocated ${formatAmount(left)}`} />
        ) : null}
      </View>
      {left < 0 ? (
        <AppText variant="caption" tone="negative">
          {formatAmount(-left)} more allocated than came in
        </AppText>
      ) : null}
    </View>
  );
}

/** A swatch and what it stands for. */
function LegendKey({ colour, label }: { colour: string; label: string }) {
  return (
    <View style={styles.key}>
      <View style={[styles.swatch, { backgroundColor: colour }]} />
      <AppText variant="caption" tone="muted">
        {label}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  allocation: { gap: SPACING.sm },
  // However small its share, a segment stays wide enough to see.
  segment: { minWidth: 6 },
  bar: { height: 12, borderRadius: RADIUS.pill, overflow: 'hidden', flexDirection: 'row', gap: 2 },
  legend: { flexDirection: 'row', flexWrap: 'wrap', columnGap: SPACING.md, rowGap: SPACING.xs },
  key: { flexDirection: 'row', alignItems: 'center', gap: SPACING.xs },
  swatch: { width: 8, height: 8, borderRadius: RADIUS.pill },
});
