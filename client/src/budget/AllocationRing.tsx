import { StyleSheet, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';

import { useTrackerColour, UNALLOCATED } from '@/budget/AllocationBar';
import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { formatAmount } from '@/theme/formatAmount';

type RingSlice = { key: string; name: string; budget: number };

type AllocationRingProps = {
  /** Each tracker's budget, drawn largest first, clockwise from the top. */
  slices: readonly RingSlice[];
  income: number;
  size?: number;
};

const STROKE = 26;
/** The gap between slices, along the ring. */
const GAP = 3;
/** The shortest a slice is drawn, so a small one still shows. */
const MIN_SLICE = 6;

/**
 * Income as a ring, split into the trackers' budgets and what is left unallocated, with that
 * remainder in the hole. Once the budgets come to more than the income, the ring is scaled to the
 * budgets, outlined in the negative colour, and the hole says by how much.
 */
export function AllocationRing({ slices, income, size = 220 }: AllocationRingProps) {
  const { colors, dark } = useAppTheme();
  const colourOf = useTrackerColour();
  const allocated = slices.reduce((total, slice) => total + slice.budget, 0);
  const left = income - allocated;
  const over = left < 0;
  const whole = Math.max(income, allocated);
  const radius = (size - STROKE) / 2 - (over ? 4 : 0);
  const circumference = 2 * Math.PI * radius;
  const centre = size / 2;

  const arcs = [
    ...[...slices]
      .sort((a, b) => b.budget - a.budget)
      .map((slice) => ({ key: slice.key, value: slice.budget, colour: colourOf(slice.name) })),
    { key: 'unallocated', value: Math.max(left, 0), colour: UNALLOCATED[dark ? 'dark' : 'light'] },
  ].filter((arc) => arc.value > 0);
  const gap = arcs.length > 1 ? GAP : 0;

  // A dash starts at three o'clock, so each is pushed back a quarter turn to start at twelve.
  let start = circumference / 4;
  const drawn = arcs.map((arc) => {
    const length = Math.max(whole > 0 ? (arc.value / whole) * circumference : 0, MIN_SLICE + gap);
    const segment = { ...arc, offset: start, length: length - gap };
    start -= length;
    return segment;
  });

  return (
    <View
      accessible
      role="img"
      aria-label={`${formatAmount(allocated)} of ${formatAmount(income)} income allocated`}
      style={[styles.ring, { width: size, height: size }]}
    >
      <Svg width={size} height={size}>
        <Circle
          cx={centre}
          cy={centre}
          r={radius}
          stroke={colors.surfaceMuted}
          strokeWidth={STROKE}
          fill="none"
        />
        {drawn.map((arc) => (
          <Circle
            key={arc.key}
            cx={centre}
            cy={centre}
            r={radius}
            stroke={arc.colour}
            strokeWidth={STROKE}
            strokeDasharray={`${arc.length} ${circumference - arc.length}`}
            strokeDashoffset={arc.offset}
            fill="none"
          />
        ))}
        {over ? (
          <Circle
            cx={centre}
            cy={centre}
            r={radius + STROKE / 2 + 3}
            stroke={colors.negative}
            strokeWidth={2}
            fill="none"
          />
        ) : null}
      </Svg>
      <View style={styles.hole} pointerEvents="none">
        <AppText variant="heading" tone={over ? 'negative' : 'default'} style={styles.amount}>
          {formatAmount(Math.abs(left))}
        </AppText>
        <AppText variant="caption" tone="muted">
          {over ? 'over-allocated' : 'unallocated'}
        </AppText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  ring: { alignSelf: 'center' },
  hole: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
  amount: { fontVariant: ['tabular-nums'] },
});
