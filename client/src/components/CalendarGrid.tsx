import { useEffect, useRef } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { NO_FOCUS_RING } from '@/components/fieldFocus';
import { type InteractionState } from '@/components/interaction';
import { focusOnWeb, webProps, type KeyEvent } from '@/components/webOnly';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING, type Palette } from '@/theme/tokens';

/** One day, month or year to choose. */
export type CalendarCell = {
  /** What choosing the cell gives, e.g. a `YYYY-MM-DD` date. Unique in its grid. */
  key: string;
  /** What the cell shows, e.g. `12`, `Nov` or `2026`. */
  label: string;
  /** What assistive technology announces, e.g. `Thursday 12 November 2026, today`. */
  spoken: string;
  /** Holds the chosen date. */
  selected: boolean;
  /** Holds today. */
  current: boolean;
};

/** A column's heading, e.g. `M` for Monday. */
export type CalendarColumn = { label: string; spoken: string };

type CalendarGridProps = {
  /** Names the grid for assistive technology, e.g. `November 2026`. */
  label: string;
  /** The cells, row by row. Null leaves a gap, as before a month's first day. */
  rows: readonly (readonly (CalendarCell | null)[])[];
  /** Headings over the columns, e.g. the days of the week. */
  columns?: readonly CalendarColumn[];
  /** A day is a circle in a close-set grid; a tile is as wide as its column, for months and years. */
  shape: 'day' | 'tile';
  /** The key of the one cell in the tab order. */
  tabStop: string;
  /**
   * Focus moves onto the tab stop when the grid appears, and again each time this changes. Only the
   * web moves focus.
   */
  focusRequest: number;
  onSelect: (key: string) => void;
  /** A key was pressed in the grid, for the keys that move the tab stop. */
  onKeyDown: (event: KeyEvent) => void;
};

/**
 * A grid of days, months or years to pick one from: the chosen one filled, today's ringed. Only one
 * cell is in the tab order, and whoever draws the grid says which, moving it as the keys ask.
 */
export function CalendarGrid({
  label,
  rows,
  columns,
  shape,
  tabStop,
  focusRequest,
  onSelect,
  onKeyDown,
}: CalendarGridProps) {
  const { colors } = useAppTheme();
  const tabStopCell = useRef<View>(null);

  useEffect(() => {
    focusOnWeb(tabStopCell.current);
  }, [focusRequest]);

  const cellStyle = shape === 'day' ? styles.dayCell : styles.tileCell;
  const buttonStyle = shape === 'day' ? styles.day : styles.tile;

  return (
    <View
      role="grid"
      aria-label={label}
      style={shape === 'tile' && styles.tiles}
      {...webProps({ onKeyDown })}
    >
      {columns ? (
        <View role="row" style={styles.row}>
          {columns.map((column, index) => (
            <View key={index} role="columnheader" aria-label={column.spoken} style={cellStyle}>
              <AppText variant="caption" tone="muted" aria-hidden>
                {column.label}
              </AppText>
            </View>
          ))}
        </View>
      ) : null}
      {rows.map((row, rowIndex) => (
        <View key={rowIndex} role="row" style={[styles.row, shape === 'tile' && styles.tileRow]}>
          {row.map((cell, column) => {
            if (cell === null) return <View key={column} style={cellStyle} />;
            const { selected, current } = cell;
            return (
              <View
                key={cell.key}
                aria-selected={selected}
                style={cellStyle}
                {...webProps({ role: 'gridcell' })}
              >
                <Pressable
                  ref={cell.key === tabStop ? tabStopCell : undefined}
                  role="button"
                  aria-label={cell.spoken}
                  aria-current={current ? 'date' : undefined}
                  focusable={cell.key === tabStop}
                  onPress={() => onSelect(cell.key)}
                  style={(state: InteractionState) => [
                    buttonStyle,
                    NO_FOCUS_RING,
                    {
                      backgroundColor: fill(colors, cell, state),
                      borderColor: ring(colors, cell, state),
                    },
                  ]}
                >
                  <AppText
                    tone={current && !selected ? 'accent' : 'default'}
                    style={[
                      styles.text,
                      selected && { color: colors.onAccent },
                      (selected || current) && styles.marked,
                    ]}
                  >
                    {cell.label}
                  </AppText>
                </Pressable>
              </View>
            );
          })}
        </View>
      ))}
    </View>
  );
}

type CellColours = Pick<Palette, 'accent' | 'border' | 'text'>;

/** A cell's fill: the accent for the chosen one, else a shade while pressed or under the pointer. */
function fill(colors: CellColours, { selected }: CalendarCell, state: InteractionState): string {
  if (selected) return colors.accent;
  return state.pressed || state.hovered ? colors.border : 'transparent';
}

/**
 * A cell's ring: the text colour when the chosen one has focus, so it shows against the accent fill,
 * the accent for any other focused cell and for today's, else none.
 */
function ring(
  colors: CellColours,
  { selected, current }: CalendarCell,
  { focused }: InteractionState,
): string {
  if (focused) return selected ? colors.text : colors.accent;
  return current && !selected ? colors.accent : 'transparent';
}

const DAY_SIZE = 38;

const styles = StyleSheet.create({
  row: { flexDirection: 'row' },
  dayCell: { flex: 1, minHeight: DAY_SIZE + 2, alignItems: 'center', justifyContent: 'center' },
  day: {
    width: DAY_SIZE,
    height: DAY_SIZE,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  tiles: { gap: SPACING.sm, paddingTop: SPACING.xs },
  tileRow: { gap: SPACING.sm },
  tileCell: { flex: 1 },
  tile: {
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  text: { fontVariant: ['tabular-nums'] },
  marked: { fontWeight: '600' },
});
