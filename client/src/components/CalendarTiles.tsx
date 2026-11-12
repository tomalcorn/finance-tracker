import { useEffect, useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { NO_FOCUS_RING } from '@/components/fieldFocus';
import { type InteractionState } from '@/components/interaction';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING, type Palette } from '@/theme/tokens';

/** Tiles in a row of the grid. */
const COLUMNS = 3;

/** One month or year to choose. */
export type CalendarTile = {
  key: string;
  /** What the tile shows, e.g. `Nov` or `2026`. */
  label: string;
  /** What assistive technology announces, e.g. `November 2026`. */
  spoken: string;
  /** Holds the chosen date. */
  selected: boolean;
  /** Holds today. */
  current: boolean;
};

type KeyEvent = { key: string; preventDefault: () => void };

/** A `Pressable` that can be focused from code, which only the web's can. */
type Focusable = View & { focus?: () => void };

type CalendarTilesProps = {
  /** Names the grid for assistive technology, e.g. `Months of 2026`. */
  label: string;
  tiles: readonly CalendarTile[];
  /**
   * The tile in the tab order to begin with, e.g. the month the calendar was on; when it is off the
   * grid, the chosen tile, else today's, else the first.
   */
  initialIndex?: number;
  /** Move focus onto the grid as it appears. Only the web can. */
  autoFocus: boolean;
  onSelect: (index: number) => void;
  /** The keys ran off the start (-1) or end (1) of the grid; `index` is where they landed on the next page. */
  onPage: (direction: -1 | 1, index: number) => void;
  /** Escape was pressed in the grid. */
  onDismiss: () => void;
};

/**
 * Months or years as a grid of tiles, three to a row, styled as `Calendar`'s days are: the chosen
 * one filled, today's ringed. The arrow keys move between tiles and on to the next page at an edge.
 */
export function CalendarTiles({
  label,
  tiles,
  initialIndex,
  autoFocus,
  onSelect,
  onPage,
  onDismiss,
}: CalendarTilesProps) {
  const { colors } = useAppTheme();
  const [cursor, setCursor] = useState(() => {
    if (initialIndex !== undefined && initialIndex >= 0 && initialIndex < tiles.length) {
      return initialIndex;
    }
    const selected = tiles.findIndex((tile) => tile.selected);
    if (selected !== -1) return selected;
    return Math.max(
      tiles.findIndex((tile) => tile.current),
      0,
    );
  });
  const refs = useRef<(Focusable | null)[]>([]);
  const pendingFocus = useRef(autoFocus && Platform.OS === 'web');

  useEffect(() => {
    if (!pendingFocus.current) return;
    pendingFocus.current = false;
    refs.current[cursor]?.focus?.();
  }, [cursor]);

  function moveBy(step: number) {
    const next = cursor + step;
    if (next < 0) onPage(-1, next + tiles.length);
    else if (next >= tiles.length) onPage(1, next - tiles.length);
    else {
      pendingFocus.current = Platform.OS === 'web';
      setCursor(next);
    }
  }

  const KEY_STEPS: Record<string, number> = {
    ArrowLeft: -1,
    ArrowRight: 1,
    ArrowUp: -COLUMNS,
    ArrowDown: COLUMNS,
  };

  function keyDown(event: KeyEvent) {
    const step = KEY_STEPS[event.key];
    if (step !== undefined) {
      event.preventDefault();
      moveBy(step);
    } else if (event.key === 'Escape') {
      event.preventDefault();
      onDismiss();
    }
  }

  const rows: CalendarTile[][] = [];
  for (let start = 0; start < tiles.length; start += COLUMNS) {
    rows.push(tiles.slice(start, start + COLUMNS));
  }

  return (
    <View
      role="grid"
      aria-label={label}
      style={styles.grid}
      {...({ onKeyDown: keyDown } as object)}
    >
      {rows.map((row, rowIndex) => (
        <View key={rowIndex} role="row" style={styles.row}>
          {row.map((tile, column) => {
            const index = rowIndex * COLUMNS + column;
            return (
              <View
                key={tile.key}
                style={styles.cell}
                // React Native's roles leave out `gridcell`, which a grid's cells must be.
                {...({ role: 'gridcell', 'aria-selected': tile.selected } as object)}
              >
                <Pressable
                  ref={(element) => {
                    refs.current[index] = element;
                  }}
                  role="button"
                  aria-label={`${tile.spoken}${tile.current ? ', current' : ''}`}
                  aria-current={tile.current ? 'date' : undefined}
                  focusable={index === cursor}
                  onPress={() => onSelect(index)}
                  onFocus={() => setCursor(index)}
                  style={(state: InteractionState) => [
                    styles.tile,
                    NO_FOCUS_RING,
                    {
                      backgroundColor: tile.selected
                        ? colors.accent
                        : state.pressed || state.hovered
                          ? colors.border
                          : 'transparent',
                      borderColor: tileBorder(colors, tile, state.focused),
                    },
                  ]}
                >
                  <AppText
                    tone={tile.current && !tile.selected ? 'accent' : 'default'}
                    style={[
                      tile.selected && { color: colors.onAccent },
                      (tile.selected || tile.current) && styles.marked,
                    ]}
                  >
                    {tile.label}
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

/** A tile's ring, as `Calendar` draws a day's: focus first, then today's accent. */
function tileBorder(
  colors: Pick<Palette, 'accent' | 'text'>,
  { selected, current }: CalendarTile,
  focused?: boolean,
): string {
  if (focused) return selected ? colors.text : colors.accent;
  return current && !selected ? colors.accent : 'transparent';
}

const styles = StyleSheet.create({
  grid: { gap: SPACING.sm, paddingTop: SPACING.xs },
  row: { flexDirection: 'row', gap: SPACING.sm },
  cell: { flex: 1 },
  tile: {
    height: 52,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  marked: { fontWeight: '600' },
});
