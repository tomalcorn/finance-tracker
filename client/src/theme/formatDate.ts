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
