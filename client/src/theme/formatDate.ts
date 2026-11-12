/** A `YYYY-MM-DD` date as a local calendar date, without the UTC shift `new Date(text)` applies. */
function calendarDate(date: string): Date {
  const [year = 0, month = 1, day = 1] = date.split('-').map(Number);
  return new Date(year, month - 1, day);
}

const DAY = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
const DAY_OF_MONTH = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });
const MONTH = new Intl.DateTimeFormat('en-GB', { month: 'long' });
const MONTH_SHORT = new Intl.DateTimeFormat('en-GB', { month: 'short' });
const MONTH_YEAR = new Intl.DateTimeFormat('en-GB', { month: 'long', year: 'numeric' });

/** Whether `text` is a real calendar date written `YYYY-MM-DD`. */
export function isCalendarDate(text: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) return false;
  const [year = 0, month = 0, day = 0] = text.split('-').map(Number);
  const date = new Date(year, month - 1, day);
  return date.getMonth() === month - 1 && date.getDate() === day;
}

/** Format a `YYYY-MM-DD` date for a list, e.g. `Sat 1 Nov`. */
export function formatDay(date: string): string {
  return DAY.format(calendarDate(date));
}

/** Format a `YYYY-MM-DD` date with no weekday, where space is tight, e.g. `1 Nov`. */
export function formatDayOfMonth(date: string): string {
  return DAY_OF_MONTH.format(calendarDate(date));
}

/** The month's name of a `YYYY-MM-DD` date, e.g. `November`. */
export function formatMonth(date: string): string {
  return MONTH.format(calendarDate(date));
}

/** The month's short name of a `YYYY-MM-DD` date, for a chart axis, e.g. `Nov`. */
export function formatMonthShort(date: string): string {
  return MONTH_SHORT.format(calendarDate(date));
}

/** The month and year of a `YYYY-MM-DD` date, e.g. `November 2026`. */
export function formatMonthYear(date: string): string {
  return MONTH_YEAR.format(calendarDate(date));
}

/** Whether two `YYYY-MM-DD` dates fall in the same calendar month. */
export function sameMonth(a: string, b: string): boolean {
  return a.slice(0, 7) === b.slice(0, 7);
}

const LONG_DAY = new Intl.DateTimeFormat('en-GB', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
});

/** A `YYYY-MM-DD` date as a count of days, free of time zones and daylight saving. */
function dayNumber(date: string): number {
  const [year = 0, month = 1, day = 1] = date.split('-').map(Number);
  return Date.UTC(year, month - 1, day) / 86_400_000;
}

/** The `YYYY-MM-DD` date `days` days after `date` (before it, when negative). */
export function addDays(date: string, days: number): string {
  return new Date((dayNumber(date) + days) * 86_400_000).toISOString().slice(0, 10);
}

/** `Today`, `Yesterday` or `Tomorrow` for a `YYYY-MM-DD` date that is one of them, else null. */
export function relativeDayName(date: string, today: string): string | null {
  const offset = dayNumber(date) - dayNumber(today);
  if (offset === 0) return 'Today';
  if (offset === -1) return 'Yesterday';
  if (offset === 1) return 'Tomorrow';
  return null;
}

/** Format a `YYYY-MM-DD` date for a field, e.g. `Sat 1 Nov`, adding the year outside `today`'s. */
export function formatFieldDay(date: string, today: string): string {
  const day = formatDay(date);
  return date.slice(0, 4) === today.slice(0, 4) ? day : `${day} ${date.slice(0, 4)}`;
}

/** Format a `YYYY-MM-DD` date in full, for assistive technology, e.g. `Saturday 1 November 2026`. */
export function formatLongDay(date: string): string {
  return LONG_DAY.format(calendarDate(date));
}
