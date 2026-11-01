/** A `YYYY-MM-DD` date as a local calendar date, without the UTC shift `new Date(text)` applies. */
function calendarDate(date: string): Date {
  const [year = 0, month = 1, day = 1] = date.split('-').map(Number);
  return new Date(year, month - 1, day);
}

const DAY = new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
const MONTH = new Intl.DateTimeFormat('en-GB', { month: 'long' });

/** Format a `YYYY-MM-DD` date for a list, e.g. `Sat 1 Nov`. */
export function formatDay(date: string): string {
  return DAY.format(calendarDate(date));
}

/** The month's name of a `YYYY-MM-DD` date, e.g. `November`. */
export function formatMonth(date: string): string {
  return MONTH.format(calendarDate(date));
}

/** Whether two `YYYY-MM-DD` dates fall in the same calendar month. */
export function sameMonth(a: string, b: string): boolean {
  return a.slice(0, 7) === b.slice(0, 7);
}
