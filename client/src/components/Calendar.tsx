import { useReducer, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { CalendarGrid, type CalendarCell, type CalendarColumn } from '@/components/CalendarGrid';
import { CalendarHeader, type CalendarArrow } from '@/components/CalendarHeader';
import { webProps, type KeyEvent } from '@/components/webOnly';
import {
  addDays,
  addMonths,
  monthOf,
  monthWeeks,
  shiftMonths,
  startOfWeek,
  yearOf,
} from '@/domain/dates';
import { formatLongDay, formatMonthShort, formatMonthYear } from '@/theme/formatDate';
import { SPACING } from '@/theme/tokens';

/** The first and last years the calendar reaches. */
const FIRST_YEAR = 1900;
const LAST_YEAR = 2099;

/** Years on a page of years. */
const YEARS_PER_PAGE = 12;

/** How many years before the one shown a page of years starts, so most of the page is the past. */
const YEARS_BEFORE = 10;

/** Months or years in a row of tiles. */
const TILES_PER_ROW = 3;

const WEEKDAYS: readonly CalendarColumn[] = [
  { label: 'M', spoken: 'Monday' },
  { label: 'T', spoken: 'Tuesday' },
  { label: 'W', spoken: 'Wednesday' },
  { label: 'T', spoken: 'Thursday' },
  { label: 'F', spoken: 'Friday' },
  { label: 'S', spoken: 'Saturday' },
  { label: 'S', spoken: 'Sunday' },
];

/** Where each key moves the day in the tab order, as in the WAI-ARIA date picker pattern. */
const DAY_MOVES: Record<string, (date: string, shift: boolean) => string> = {
  ArrowLeft: (date) => addDays(date, -1),
  ArrowRight: (date) => addDays(date, 1),
  ArrowUp: (date) => addDays(date, -7),
  ArrowDown: (date) => addDays(date, 7),
  Home: (date) => startOfWeek(date),
  End: (date) => addDays(startOfWeek(date), 6),
  PageUp: (date, shift) => shiftMonths(date, shift ? -12 : -1),
  PageDown: (date, shift) => shiftMonths(date, shift ? 12 : 1),
};

/** How many tiles each arrow key moves the month or year in the tab order. */
const TILE_STEPS: Record<string, number> = {
  ArrowLeft: -1,
  ArrowRight: 1,
  ArrowUp: -TILES_PER_ROW,
  ArrowDown: TILES_PER_ROW,
};

/** Whether the calendar reaches a date. */
function inRange(date: string): boolean {
  const year = yearOf(date);
  return year >= FIRST_YEAR && year <= LAST_YEAR;
}

/** An arrow that pages to `month`, disabled when the calendar doesn't reach it. */
function arrowTo(label: string, month: string, page: (month: string) => void): CalendarArrow {
  return { label, onPress: inRange(month) ? () => page(month) : undefined };
}

function inRows(tiles: CalendarCell[]): CalendarCell[][] {
  const rows: CalendarCell[][] = [];
  for (let start = 0; start < tiles.length; start += TILES_PER_ROW) {
    rows.push(tiles.slice(start, start + TILES_PER_ROW));
  }
  return rows;
}

/** What the calendar shows: a month's days, a year's months, or a page of years. */
type CalendarView = 'days' | 'months' | 'years';

/** How a view changes what the calendar shows. */
type CalendarNav = {
  /** Shows another month, leaving focus where it is: on the header's arrow that paged. */
  page: (month: string) => void;
  /** Shows another month and moves focus onto the grid's tab stop, as the keys do. */
  move: (month: string) => void;
  /** Changes view, on `month` if given, and moves focus onto the new grid. */
  show: (view: CalendarView, month?: string) => void;
};

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
  // The month shown. Among months or years, its tile is the one in the tab order.
  const [month, setMonth] = useState(() =>
    monthOf(value !== null && inRange(value) ? value : today),
  );
  // Focus moves onto the grid's tab stop as the calendar opens, and each time this is counted up.
  const [focusRequest, requestFocus] = useReducer((count: number) => count + 1, 0);

  const nav: CalendarNav = {
    page: setMonth,
    move(to) {
      setMonth(to);
      requestFocus();
    },
    show(next, to = month) {
      setView(next);
      setMonth(to);
      requestFocus();
    },
  };

  // Escape is taken as the key comes up, and kept from going further: a `Sheet` closes on that
  // same event, and would otherwise close along with the calendar.
  function keyUp(event: KeyEvent) {
    if (event.key !== 'Escape') return;
    event.stopPropagation();
    if (view === 'days') onDismiss();
    else nav.show(view === 'years' ? 'months' : 'days');
  }

  const shown = { value, today, month, focusRequest, nav };

  return (
    <View style={styles.calendar} {...webProps({ onKeyUp: keyUp })}>
      {view === 'days' && <DaysView {...shown} onSelect={onSelect} />}
      {view === 'months' && <MonthsView {...shown} />}
      {view === 'years' && <YearsView {...shown} />}
    </View>
  );
}

type ViewProps = Pick<CalendarProps, 'value' | 'today'> & {
  /** The month shown, as its first day. */
  month: string;
  focusRequest: number;
  nav: CalendarNav;
};

/** A month's days, Monday first. */
function DaysView({
  value,
  today,
  month,
  focusRequest,
  nav,
  onSelect,
}: ViewProps & Pick<CalendarProps, 'onSelect'>) {
  // The day the keys last moved to. It keeps the tab order for as long as its month is shown;
  // on another month the chosen day or today takes it, else the 1st.
  const [cursor, setCursor] = useState(value ?? today);
  const tabStop =
    [cursor, value, today].find((date) => date !== null && monthOf(date) === month) ?? month;

  function keyDown(event: KeyEvent) {
    const move = DAY_MOVES[event.key];
    if (!move) return;
    event.preventDefault();
    const date = move(tabStop, event.shiftKey ?? false);
    if (!inRange(date)) return;
    setCursor(date);
    nav.move(monthOf(date));
  }

  const rows = monthWeeks(month).map((week) =>
    week.map((date) => {
      if (date === null) return null;
      const isToday = date === today;
      return {
        key: date,
        label: String(Number(date.slice(8))),
        spoken: `${formatLongDay(date)}${isToday ? ', today' : ''}`,
        selected: date === value,
        current: isToday,
      };
    }),
  );

  return (
    <>
      <CalendarHeader
        title={formatMonthYear(month)}
        zoomOut={{ hint: 'choose a month', onPress: () => nav.show('months') }}
        previous={arrowTo('Previous month', addMonths(month, -1), nav.page)}
        next={arrowTo('Next month', addMonths(month, 1), nav.page)}
      />
      <CalendarGrid
        label={formatMonthYear(month)}
        rows={rows}
        columns={WEEKDAYS}
        shape="day"
        tabStop={tabStop}
        focusRequest={focusRequest}
        onSelect={onSelect}
        onKeyDown={keyDown}
      />
    </>
  );
}

/** The months of the year shown, to jump to one. */
function MonthsView({ value, today, month, focusRequest, nav }: ViewProps) {
  const year = yearOf(month);
  const january = `${month.slice(0, 4)}-01-01`;

  function keyDown(event: KeyEvent) {
    const step = TILE_STEPS[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const to = addMonths(month, step);
    if (inRange(to)) nav.move(to);
  }

  const tiles = Array.from({ length: 12 }, (_, index) => {
    const first = addMonths(january, index);
    const current = first === monthOf(today);
    return {
      key: first,
      label: formatMonthShort(first),
      spoken: `${formatMonthYear(first)}${current ? ', current' : ''}`,
      selected: value !== null && first === monthOf(value),
      current,
    };
  });

  return (
    <>
      <CalendarHeader
        title={String(year)}
        zoomOut={{ hint: 'choose a year', onPress: () => nav.show('years') }}
        previous={arrowTo('Previous year', addMonths(month, -12), nav.page)}
        next={arrowTo('Next year', addMonths(month, 12), nav.page)}
      />
      <CalendarGrid
        label={`Months of ${year}`}
        rows={inRows(tiles)}
        shape="tile"
        tabStop={month}
        focusRequest={focusRequest}
        onSelect={(first) => nav.show('days', first)}
        onKeyDown={keyDown}
      />
    </>
  );
}

/** The first year of the page of years nearest to one starting at `year` that the calendar reaches. */
function pageFrom(year: number): number {
  return Math.min(Math.max(year, FIRST_YEAR), LAST_YEAR - YEARS_PER_PAGE + 1);
}

/** A page of years, to jump to one. The month shown keeps its place in whichever year is picked. */
function YearsView({ value, today, month, focusRequest, nav }: ViewProps) {
  const year = yearOf(month);
  const [firstYear, setFirstYear] = useState(() => pageFrom(year - YEARS_BEFORE));
  const lastYear = firstYear + YEARS_PER_PAGE - 1;

  const inYear = (to: number) => addMonths(month, 12 * (to - year));

  /** An arrow that turns the page, taking the year in the tab order with it. */
  function arrowToPage(label: string, first: number): CalendarArrow {
    if (first === firstYear) return { label };
    return {
      label,
      onPress: () => {
        setFirstYear(first);
        nav.page(inYear(year + first - firstYear));
      },
    };
  }

  function keyDown(event: KeyEvent) {
    const step = TILE_STEPS[event.key];
    if (step === undefined) return;
    event.preventDefault();
    const to = year + step;
    if (to < FIRST_YEAR || to > LAST_YEAR) return;
    if (to < firstYear) setFirstYear(pageFrom(firstYear - YEARS_PER_PAGE));
    if (to > lastYear) setFirstYear(pageFrom(firstYear + YEARS_PER_PAGE));
    nav.move(inYear(to));
  }

  const tiles = Array.from({ length: YEARS_PER_PAGE }, (_, index) => {
    const tileYear = firstYear + index;
    const current = tileYear === yearOf(today);
    return {
      key: String(tileYear),
      label: String(tileYear),
      spoken: `${tileYear}${current ? ', current' : ''}`,
      selected: value !== null && tileYear === yearOf(value),
      current,
    };
  });

  return (
    <>
      <CalendarHeader
        title={`${firstYear} – ${lastYear}`}
        previous={arrowToPage('Earlier years', pageFrom(firstYear - YEARS_PER_PAGE))}
        next={arrowToPage('Later years', pageFrom(firstYear + YEARS_PER_PAGE))}
      />
      <CalendarGrid
        label={`Years ${firstYear} to ${lastYear}`}
        rows={inRows(tiles)}
        shape="tile"
        tabStop={String(year)}
        focusRequest={focusRequest}
        onSelect={(tileYear) => nav.show('months', inYear(Number(tileYear)))}
        onKeyDown={keyDown}
      />
    </>
  );
}

const styles = StyleSheet.create({
  calendar: { padding: SPACING.sm, gap: SPACING.xs },
});
