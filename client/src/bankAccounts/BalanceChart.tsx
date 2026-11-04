import { useState } from 'react';
import {
  Platform,
  StyleSheet,
  View,
  type GestureResponderEvent,
  type LayoutChangeEvent,
  type PointerEvent,
  type ViewStyle,
} from 'react-native';
import Svg, { Circle, Line, Path } from 'react-native-svg';

import type { BalancePoint } from '@/bankAccounts/balanceTrend';
import { dateTicks, formatValueTick, nearestIndex, valueTicks } from '@/bankAccounts/chartAxes';
import { AppText } from '@/components/AppText';
import { formatAmount } from '@/theme/formatAmount';
import { formatDay, formatDayOfMonth } from '@/theme/formatDate';
import { useAppTheme } from '@/theme/theme';
import { SPACING, TYPOGRAPHY } from '@/theme/tokens';

type BalanceChartProps = {
  /** The balance at the end of each day, oldest first, evenly spaced and at least two. */
  points: readonly BalancePoint[];
};

const PLOT_HEIGHT = 180;
/** Room above the plot for half of the top tick's label and the dot's ring. */
const PLOT_TOP = 10;
const AXIS_BAND = 26;
const TICK_LENGTH = 4;
const RIGHT_MARGIN = 16;
const LINE_WIDTH = 2;
const DOT_RADIUS = 4;
const DOT_RING = 2;
/** A rough width per character of a value label, for a gutter that fits the longest one. */
const LABEL_CHAR_WIDTH = 10;
const LABEL_HEIGHT = TYPOGRAPHY.caption.lineHeight ?? 18;
/** Wide enough for any date label, which is centred on its tick. */
const DATE_LABEL_WIDTH = 64;

// A vertical drag still scrolls the page, and a sideways one follows the line.
const PAN_Y = Platform.select<ViewStyle>({
  web: { touchAction: 'pan-y' } as ViewStyle,
  default: {},
});

/**
 * An account's balance over time, with a value axis, a date axis, and a figure above that follows
 * the pointer or a finger along the line, and otherwise shows the latest balance.
 */
export function BalanceChart({ points }: BalanceChartProps) {
  const { colors } = useAppTheme();
  const [width, setWidth] = useState(0);
  const [active, setActive] = useState<number | null>(null);

  const balances = points.map((point) => point.balance);
  const ticks = valueTicks(balances);
  const dates = dateTicks(points.map((point) => point.date));
  const labels = ticks.map(formatValueTick);
  const gutter = Math.max(...labels.map((label) => label.length)) * LABEL_CHAR_WIDTH;
  const plotWidth = Math.max(width - gutter - RIGHT_MARGIN, 0);
  const low = ticks[0] ?? 0;
  const high = ticks.at(-1) ?? 0;
  const lastIndex = points.length - 1;
  const first = points[0];
  const last = points[lastIndex];
  const shown = points[active ?? lastIndex];

  function xOf(index: number): number {
    return gutter + (index / lastIndex) * plotWidth;
  }

  function yOf(value: number): number {
    return PLOT_TOP + (1 - (value - low) / (high - low)) * PLOT_HEIGHT;
  }

  function measure(event: LayoutChangeEvent) {
    setWidth(event.nativeEvent.layout.width);
  }

  function follow(x: number) {
    if (plotWidth > 0) setActive(nearestIndex(x, plotWidth, points.length));
  }

  function followTouch(event: GestureResponderEvent) {
    follow(event.nativeEvent.locationX);
  }

  function followPointer(event: PointerEvent) {
    follow(event.nativeEvent.offsetX);
  }

  function release() {
    setActive(null);
  }

  const summary =
    first && last
      ? `Balance from ${formatAmount(first.balance)} on ${formatDayOfMonth(first.date)} to ${formatAmount(last.balance)} on ${formatDayOfMonth(last.date)}, low ${formatAmount(Math.min(...balances))}, high ${formatAmount(Math.max(...balances))}`
      : undefined;

  return (
    <View style={styles.chart}>
      <View>
        <AppText variant="title" style={styles.figure}>
          {formatAmount(shown?.balance ?? 0)}
        </AppText>
        <AppText variant="caption" tone="muted">
          {shown ? formatDay(shown.date) : ' '}
        </AppText>
      </View>

      <View
        accessible
        role="img"
        aria-label={summary}
        onLayout={measure}
        style={{ height: PLOT_TOP + PLOT_HEIGHT + AXIS_BAND }}
      >
        {width > 0 ? (
          <>
            <Svg width={width} height={PLOT_TOP + PLOT_HEIGHT + AXIS_BAND}>
              {ticks.map((tick) => (
                <Line
                  key={tick}
                  x1={gutter}
                  x2={gutter + plotWidth}
                  y1={yOf(tick)}
                  y2={yOf(tick)}
                  stroke={colors.border}
                  strokeWidth={1}
                />
              ))}
              {dates.map((tick) => (
                <Line
                  key={tick.index}
                  x1={xOf(tick.index)}
                  x2={xOf(tick.index)}
                  y1={PLOT_TOP + PLOT_HEIGHT}
                  y2={PLOT_TOP + PLOT_HEIGHT + TICK_LENGTH}
                  stroke={colors.border}
                  strokeWidth={1}
                />
              ))}
              {active !== null ? (
                <Line
                  x1={xOf(active)}
                  x2={xOf(active)}
                  y1={PLOT_TOP}
                  y2={PLOT_TOP + PLOT_HEIGHT}
                  stroke={colors.textMuted}
                  strokeWidth={1}
                />
              ) : null}
              <Path
                d={balances
                  .map((value, index) => `${index === 0 ? 'M' : 'L'}${xOf(index)} ${yOf(value)}`)
                  .join(' ')}
                fill="none"
                stroke={colors.accent}
                strokeWidth={LINE_WIDTH}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {shown ? (
                <Circle
                  cx={xOf(active ?? lastIndex)}
                  cy={yOf(shown.balance)}
                  r={DOT_RADIUS}
                  fill={colors.accent}
                  stroke={colors.surface}
                  strokeWidth={DOT_RING}
                />
              ) : null}
            </Svg>

            {ticks.map((tick, index) => (
              <AppText
                key={tick}
                variant="caption"
                tone="muted"
                numberOfLines={1}
                style={[
                  styles.valueLabel,
                  { width: gutter - SPACING.xs, top: yOf(tick) - LABEL_HEIGHT / 2 },
                ]}
              >
                {labels[index]}
              </AppText>
            ))}
            {dates.map((tick) => (
              <AppText
                key={tick.index}
                variant="caption"
                tone="muted"
                numberOfLines={1}
                style={[styles.dateLabel, { left: xOf(tick.index) - DATE_LABEL_WIDTH / 2 }]}
              >
                {tick.label}
              </AppText>
            ))}

            <View
              onStartShouldSetResponder={() => true}
              onResponderGrant={followTouch}
              onResponderMove={followTouch}
              onResponderRelease={release}
              onResponderTerminate={release}
              onPointerMove={followPointer}
              onPointerLeave={release}
              style={[styles.hitArea, PAN_Y, { left: gutter, width: plotWidth }]}
            />
          </>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  chart: { gap: SPACING.md },
  figure: { fontVariant: ['tabular-nums'] },
  valueLabel: { position: 'absolute', left: 0, textAlign: 'right', fontVariant: ['tabular-nums'] },
  dateLabel: {
    position: 'absolute',
    top: PLOT_TOP + PLOT_HEIGHT + TICK_LENGTH + 2,
    width: DATE_LABEL_WIDTH,
    textAlign: 'center',
  },
  hitArea: { position: 'absolute', top: 0, height: PLOT_TOP + PLOT_HEIGHT },
});
