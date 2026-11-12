import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { useEffect, useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import {
  addMonths,
  monthOf,
  monthWeeks,
  shiftMonths,
  startOfWeek,
} from '@/components/calendarMonth';
import { NO_FOCUS_RING } from '@/components/fieldFocus';
import { type InteractionState } from '@/components/interaction';
import { useAppTheme } from '@/theme/theme';
import { addDays, formatLongDay, formatMonthYear } from '@/theme/formatDate';
import { RADIUS, SPACING, type Palette } from '@/theme/tokens';

const PREVIOUS: SymbolViewProps['name'] = { ios: 'chevron.left', web: 'chevron_left' };
const NEXT: SymbolViewProps['name'] = { ios: 'chevron.right', web: 'chevron_right' };

const WEEKDAYS = [
  ['M', 'Monday'],
  ['T', 'Tuesday'],
  ['W', 'Wednesday'],
  ['T', 'Thursday'],
  ['F', 'Friday'],
  ['S', 'Saturday'],
  ['S', 'Sunday'],
] as const;

/** Where each navigation key moves the focused day, as in the WAI-ARIA date picker pattern. */
const KEY_MOVES: Record<string, (date: string, shift: boolean) => string> = {
  ArrowLeft: (date) => addDays(date, -1),
  ArrowRight: (date) => addDays(date, 1),
  ArrowUp: (date) => addDays(date, -7),
  ArrowDown: (date) => addDays(date, 7),
  Home: (date) => startOfWeek(date),
  End: (date) => addDays(startOfWeek(date), 6),
  PageUp: (date, shift) => shiftMonths(date, shift ? -12 : -1),
  PageDown: (date, shift) => shiftMonths(date, shift ? 12 : 1),
};

type KeyEvent = { key: string; shiftKey?: boolean; preventDefault: () => void };

/** A `Pressable` that can be focused from code, which only the web's can. */
type Focusable = View & { focus?: () => void };

type CalendarProps = {
  /** The chosen `YYYY-MM-DD` date, or null for none. */
  value: string | null;
  /** Today's `YYYY-MM-DD` date, marked on the grid. */
  today: string;
  onSelect: (date: string) => void;
  /** Escape was pressed in the grid. */
  onDismiss: () => void;
};

/**
 * A month of days to pick one from, in the app's theme. On the web it takes focus as it opens, on
 * the chosen day, and the arrow, Home, End and Page keys move between days and months.
 */
export function Calendar({ value, today, onSelect, onDismiss }: CalendarProps) {
  const { colors } = useAppTheme();
  const [month, setMonth] = useState(() => monthOf(value ?? today));
  // The day that takes focus from the keyboard: the only one in the tab order.
  const [cursor, setCursor] = useState(() => value ?? today);
  const days = useRef(new Map<string, Focusable | null>());
  const pendingFocus = useRef(Platform.OS === 'web');

  // When the month changes by its buttons, the cursor stays put if it can, else moves onto the month.
  const cursorInMonth = monthOf(cursor) === month ? cursor : null;
  const tabStop =
    cursorInMonth ??
    [value, today].find((date) => date !== null && monthOf(date) === month) ??
    month;

  useEffect(() => {
    if (!pendingFocus.current) return;
    pendingFocus.current = false;
    days.current.get(tabStop)?.focus?.();
  }, [tabStop]);

  function moveTo(date: string) {
    pendingFocus.current = Platform.OS === 'web';
    setCursor(date);
    setMonth(monthOf(date));
  }

  function keyDown(event: KeyEvent) {
    const move = KEY_MOVES[event.key];
    if (move) {
      event.preventDefault();
      moveTo(move(tabStop, event.shiftKey ?? false));
    } else if (event.key === 'Escape') {
      event.preventDefault();
      onDismiss();
    }
  }

  function monthButton(name: SymbolViewProps['name'], label: string, months: number) {
    return (
      <Pressable
        role="button"
        aria-label={label}
        hitSlop={4}
        onPress={() => setMonth(addMonths(month, months))}
        style={(state: InteractionState) => [
          styles.monthButton,
          NO_FOCUS_RING,
          {
            backgroundColor: state.pressed || state.hovered ? colors.border : 'transparent',
            borderColor: state.focused ? colors.accent : 'transparent',
          },
        ]}
      >
        <SymbolView name={name} size={20} tintColor={colors.text} />
      </Pressable>
    );
  }

  return (
    <View style={styles.calendar}>
      <View style={styles.header}>
        {monthButton(PREVIOUS, 'Previous month', -1)}
        <AppText variant="label" aria-live="polite" style={styles.monthName}>
          {formatMonthYear(month)}
        </AppText>
        {monthButton(NEXT, 'Next month', 1)}
      </View>
      <View role="grid" aria-label={formatMonthYear(month)} {...({ onKeyDown: keyDown } as object)}>
        <View role="row" style={styles.week}>
          {WEEKDAYS.map(([initial, name], index) => (
            <View key={index} role="columnheader" aria-label={name} style={styles.cell}>
              <AppText variant="caption" tone="muted" aria-hidden>
                {initial}
              </AppText>
            </View>
          ))}
        </View>
        {monthWeeks(month).map((week, row) => (
          <View key={row} role="row" style={styles.week}>
            {week.map((date, column) => {
              if (date === null) return <View key={column} style={styles.cell} />;
              const selected = date === value;
              const isToday = date === today;
              return (
                <View
                  key={column}
                  style={styles.cell}
                  // React Native's roles leave out `gridcell`, which a grid's cells must be.
                  {...({ role: 'gridcell', 'aria-selected': selected } as object)}
                >
                  <Pressable
                    ref={(day) => {
                      days.current.set(date, day);
                    }}
                    role="button"
                    aria-current={isToday ? 'date' : undefined}
                    aria-label={`${formatLongDay(date)}${isToday ? ', today' : ''}`}
                    focusable={date === tabStop}
                    onPress={() => onSelect(date)}
                    onFocus={() => setCursor(date)}
                    style={(state: InteractionState) => [
                      styles.day,
                      NO_FOCUS_RING,
                      {
                        backgroundColor: selected
                          ? colors.accent
                          : state.pressed || state.hovered
                            ? colors.border
                            : 'transparent',
                        borderColor: dayBorder(colors, {
                          selected,
                          isToday,
                          focused: state.focused,
                        }),
                      },
                    ]}
                  >
                    <AppText
                      tone={isToday && !selected ? 'accent' : 'default'}
                      style={[
                        styles.dayNumber,
                        selected && { color: colors.onAccent },
                        (selected || isToday) && styles.marked,
                      ]}
                    >
                      {Number(date.slice(8))}
                    </AppText>
                  </Pressable>
                </View>
              );
            })}
          </View>
        ))}
      </View>
    </View>
  );
}

/**
 * A day's ring: the text colour when the chosen day has focus, so it shows against the accent fill,
 * the accent for any other focused day and for today, else none.
 */
function dayBorder(
  colors: Pick<Palette, 'accent' | 'text'>,
  { selected, isToday, focused }: { selected: boolean; isToday: boolean; focused?: boolean },
): string {
  if (focused) return selected ? colors.text : colors.accent;
  return isToday && !selected ? colors.accent : 'transparent';
}

const DAY_SIZE = 38;

const styles = StyleSheet.create({
  calendar: { padding: SPACING.sm, gap: SPACING.xs },
  header: { flexDirection: 'row', alignItems: 'center', gap: SPACING.sm },
  monthName: { flex: 1, textAlign: 'center' },
  monthButton: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  week: { flexDirection: 'row' },
  cell: { flex: 1, minHeight: DAY_SIZE + 2, alignItems: 'center', justifyContent: 'center' },
  day: {
    width: DAY_SIZE,
    height: DAY_SIZE,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  dayNumber: { fontVariant: ['tabular-nums'] },
  marked: { fontWeight: '600' },
});
