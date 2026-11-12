import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { useEffect, useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { CalendarTiles, type CalendarTile } from '@/components/CalendarTiles';
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
import { addDays, formatLongDay, formatMonthShort, formatMonthYear } from '@/theme/formatDate';
import { RADIUS, SPACING, type Palette } from '@/theme/tokens';

const PREVIOUS: SymbolViewProps['name'] = { ios: 'chevron.left', web: 'chevron_left' };
const NEXT: SymbolViewProps['name'] = { ios: 'chevron.right', web: 'chevron_right' };
const ZOOM_OUT: SymbolViewProps['name'] = { ios: 'chevron.down', web: 'expand_more' };

const WEEKDAYS = [
  ['M', 'Monday'],
  ['T', 'Tuesday'],
  ['W', 'Wednesday'],
  ['T', 'Thursday'],
  ['F', 'Friday'],
  ['S', 'Saturday'],
  ['S', 'Sunday'],
] as const;

/** Years on a page of the year grid. */
const YEARS_PER_PAGE = 12;

/** How many years before the chosen one a page of years starts, so most of the page is the past. */
const YEARS_BEFORE = 10;

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

/** What the calendar shows: a month's days, a year's months, or a page of years. */
type CalendarView = 'days' | 'months' | 'years';

type CalendarProps = {
  /** The chosen `YYYY-MM-DD` date, or null for none. */
  value: string | null;
  /** Today's `YYYY-MM-DD` date, marked on the grid. */
  today: string;
  onSelect: (date: string) => void;
  /** Escape was pressed on the days. */
  onDismiss: () => void;
};

/**
 * A month of days to pick one from, in the app's theme. Its banner opens the year's months, and the
 * year's banner a page of years, to jump a long way without paging month by month. On the web it
 * takes focus as it opens, on the chosen day; the arrow keys move around each grid, and Escape
 * steps back out to the days, then closes.
 */
export function Calendar({ value, today, onSelect, onDismiss }: CalendarProps) {
  const [view, setView] = useState<CalendarView>('days');
  const [month, setMonth] = useState(() => monthOf(value ?? today));
  const [firstYear, setFirstYear] = useState(0);
  // Where the keys landed when they ran off one page of tiles onto the next.
  const [tileIndex, setTileIndex] = useState<number>();
  // Whether the grid takes focus as it appears: on opening, and when a grid replaces another, but
  // not when the arrow buttons page, so focus stays on the button.
  const [autoFocus, setAutoFocus] = useState(Platform.OS === 'web');
  const year = Number(month.slice(0, 4));

  function show(next: CalendarView, { landing }: { landing?: number } = {}) {
    setView(next);
    setTileIndex(landing);
    setAutoFocus(Platform.OS === 'web');
  }

  function page(apply: () => void) {
    apply();
    setTileIndex(undefined);
    setAutoFocus(false);
  }

  if (view === 'days') {
    return (
      <View style={styles.calendar}>
        <Header
          title={formatMonthYear(month)}
          titleHint="choose a month"
          onTitle={() => show('months')}
          previous={{
            label: 'Previous month',
            onPress: () => page(() => setMonth(addMonths(month, -1))),
          }}
          next={{ label: 'Next month', onPress: () => page(() => setMonth(addMonths(month, 1))) }}
        />
        <DayGrid
          month={month}
          value={value}
          today={today}
          autoFocus={autoFocus}
          onMonth={setMonth}
          onSelect={onSelect}
          onDismiss={onDismiss}
        />
      </View>
    );
  }

  if (view === 'months') {
    const tiles: CalendarTile[] = Array.from({ length: 12 }, (_, index) => {
      const first = `${year}-${String(index + 1).padStart(2, '0')}-01`;
      return {
        key: first,
        label: formatMonthShort(first),
        spoken: formatMonthYear(first),
        selected: value !== null && monthOf(value) === first,
        current: monthOf(today) === first,
      };
    });
    return (
      <View style={styles.calendar}>
        <Header
          title={String(year)}
          titleHint="choose a year"
          onTitle={() => {
            setFirstYear(year - YEARS_BEFORE);
            show('years');
          }}
          previous={{
            label: 'Previous year',
            onPress: () => page(() => setMonth(addMonths(month, -12))),
          }}
          next={{ label: 'Next year', onPress: () => page(() => setMonth(addMonths(month, 12))) }}
        />
        <CalendarTiles
          key={`months-${year}`}
          label={`Months of ${year}`}
          tiles={tiles}
          initialIndex={tileIndex ?? Number(month.slice(5, 7)) - 1}
          autoFocus={autoFocus}
          onSelect={(index) => {
            setMonth(tiles[index]?.key ?? month);
            show('days');
          }}
          onPage={(direction, landing) => {
            setMonth(addMonths(month, 12 * direction));
            show('months', { landing });
          }}
          onDismiss={() => show('days')}
        />
      </View>
    );
  }

  const lastYear = firstYear + YEARS_PER_PAGE - 1;
  const tiles: CalendarTile[] = Array.from({ length: YEARS_PER_PAGE }, (_, index) => {
    const tileYear = String(firstYear + index);
    return {
      key: tileYear,
      label: tileYear,
      spoken: tileYear,
      selected: value !== null && value.startsWith(tileYear),
      current: today.startsWith(tileYear),
    };
  });
  return (
    <View style={styles.calendar}>
      <Header
        title={`${firstYear} – ${lastYear}`}
        previous={{
          label: 'Earlier years',
          onPress: () => page(() => setFirstYear(firstYear - YEARS_PER_PAGE)),
        }}
        next={{
          label: 'Later years',
          onPress: () => page(() => setFirstYear(firstYear + YEARS_PER_PAGE)),
        }}
      />
      <CalendarTiles
        key={`years-${firstYear}`}
        label={`Years ${firstYear} to ${lastYear}`}
        tiles={tiles}
        initialIndex={tileIndex ?? year - firstYear}
        autoFocus={autoFocus}
        onSelect={(index) => {
          setMonth(`${firstYear + index}-${month.slice(5)}`);
          show('months');
        }}
        onPage={(direction, landing) => {
          setFirstYear(firstYear + YEARS_PER_PAGE * direction);
          show('years', { landing });
        }}
        onDismiss={() => show('months')}
      />
    </View>
  );
}

type HeaderButton = { label: string; onPress: () => void };

type HeaderProps = {
  title: string;
  /** Makes the title a button that zooms out, announced as the title and this, e.g. `choose a month`. */
  titleHint?: string;
  onTitle?: () => void;
  previous: HeaderButton;
  next: HeaderButton;
};

/** The calendar's banner: what it shows, between buttons that page back and forward. */
function Header({ title, titleHint, onTitle, previous, next }: HeaderProps) {
  const { colors } = useAppTheme();

  function arrow(name: SymbolViewProps['name'], { label, onPress }: HeaderButton) {
    return (
      <Pressable
        role="button"
        aria-label={label}
        hitSlop={4}
        onPress={onPress}
        style={(state: InteractionState) => [
          styles.arrow,
          NO_FOCUS_RING,
          headerButtonColours(colors, state),
        ]}
      >
        <SymbolView name={name} size={20} tintColor={colors.text} />
      </Pressable>
    );
  }

  return (
    <View style={styles.header}>
      {arrow(PREVIOUS, previous)}
      <View style={styles.titleSlot}>
        {onTitle ? (
          <Pressable
            role="button"
            aria-label={`${title}, ${titleHint}`}
            onPress={onTitle}
            style={(state: InteractionState) => [
              styles.title,
              NO_FOCUS_RING,
              headerButtonColours(colors, state),
            ]}
          >
            <AppText variant="label" aria-live="polite">
              {title}
            </AppText>
            <SymbolView name={ZOOM_OUT} size={16} tintColor={colors.textMuted} />
          </Pressable>
        ) : (
          <AppText variant="label" aria-live="polite" style={styles.titleText}>
            {title}
          </AppText>
        )}
      </View>
      {arrow(NEXT, next)}
    </View>
  );
}

function headerButtonColours(colors: Palette, state: InteractionState) {
  return {
    backgroundColor: state.pressed || state.hovered ? colors.border : 'transparent',
    borderColor: state.focused ? colors.accent : 'transparent',
  };
}

type DayGridProps = {
  /** The month shown, as its first day. */
  month: string;
  value: string | null;
  today: string;
  /** Move focus onto the grid's tab stop as it appears. Only the web can. */
  autoFocus: boolean;
  /** The keys moved onto another month. */
  onMonth: (month: string) => void;
  onSelect: (date: string) => void;
  onDismiss: () => void;
};

/** A month's days, Monday first, with the keyboard moving a single tab stop between them. */
function DayGrid({ month, value, today, autoFocus, onMonth, onSelect, onDismiss }: DayGridProps) {
  const { colors } = useAppTheme();
  // The day that takes focus from the keyboard: the only one in the tab order.
  const [cursor, setCursor] = useState(() => value ?? today);
  const days = useRef(new Map<string, Focusable | null>());
  const pendingFocus = useRef(autoFocus && Platform.OS === 'web');

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

  function keyDown(event: KeyEvent) {
    const move = KEY_MOVES[event.key];
    if (move) {
      event.preventDefault();
      const date = move(tabStop, event.shiftKey ?? false);
      pendingFocus.current = Platform.OS === 'web';
      setCursor(date);
      onMonth(monthOf(date));
    } else if (event.key === 'Escape') {
      event.preventDefault();
      onDismiss();
    }
  }

  return (
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
  titleSlot: { flex: 1, alignItems: 'center' },
  title: {
    minHeight: 36,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    paddingLeft: SPACING.md,
    paddingRight: SPACING.sm,
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  titleText: { lineHeight: 36 },
  arrow: {
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
