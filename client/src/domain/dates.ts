/**
 * Arithmetic on `YYYY-MM-DD` calendar dates. A month is written as the date of its first day, and a
 * week starts on Monday. Everything works in UTC, so no time zone or change of the clocks moves a day.
 */

const MS_PER_DAY = 86_400_000;

/** A date's year, month (1 to 12) and day. A `YYYY-MM` month counts as its first day. */
export function dateParts(date: string): [year: number, month: number, day: number] {
  const [year = 0, month = 1, day = 1] = date.split('-').map(Number);
  return [year, month, day];
}

/** A date as a count of days, so that two can be compared or subtracted. */
export function dayNumber(date: string): number {
  const [year, month, day] = dateParts(date);
  return Date.UTC(year, month - 1, day) / MS_PER_DAY;
}

/** The date a `dayNumber` counts to. */
export function dateOfDay(day: number): string {
  return new Date(day * MS_PER_DAY).toISOString().slice(0, 10);
}

/** The date `days` days after `date` (before it, when negative). */
export function addDays(date: string, days: number): string {
  return dateOfDay(dayNumber(date) + days);
}

/** The year a date falls in. */
export function yearOf(date: string): number {
  return dateParts(date)[0];
}

/** The month a date falls in, as its first day. */
export function monthOf(date: string): string {
  return `${date.slice(0, 7)}-01`;
}

/** The first day of the month `months` after `date`'s (before it, when negative). */
export function addMonths(date: string, months: number): string {
  const [year, month] = dateParts(date);
  return dateOfDay(Date.UTC(year, month - 1 + months, 1) / MS_PER_DAY);
}

/** The same day `months` months on, or the month's last day when it is shorter, e.g. 31 Jan → 28 Feb. */
export function shiftMonths(date: string, months: number): string {
  const [, , day] = dateParts(date);
  const month = addMonths(date, months);
  const lastDay = dateParts(addDays(addMonths(month, 1), -1))[2];
  return addDays(month, Math.min(day, lastDay) - 1);
}

/** The Monday on or before a date. */
export function startOfWeek(date: string): string {
  const day = dayNumber(date);
  // Day 0, 1 January 1970, was a Thursday.
  return dateOfDay(day - ((((day + 3) % 7) + 7) % 7));
}

/**
 * A month laid out as weeks from Monday to Sunday, each a row of seven dates, with null for the days
 * before the 1st and after the last day.
 */
export function monthWeeks(month: string): (string | null)[][] {
  const lead = dayNumber(month) - dayNumber(startOfWeek(month));
  const length = dayNumber(addMonths(month, 1)) - dayNumber(month);
  const cells: (string | null)[] = Array.from({ length: lead }, () => null);
  for (let day = 0; day < length; day++) cells.push(addDays(month, day));
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: (string | null)[][] = [];
  for (let start = 0; start < cells.length; start += 7) weeks.push(cells.slice(start, start + 7));
  return weeks;
}
