/**
 * The arithmetic behind `Calendar`: months as the `YYYY-MM-01` date of their first day, and weeks
 * that start on Monday. Everything works in UTC, so no time zone or daylight saving shift moves a day.
 */

function parts(date: string): [year: number, month: number, day: number] {
  const [year = 0, month = 1, day = 1] = date.split('-').map(Number);
  return [year, month, day];
}

function iso(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** The month a `YYYY-MM-DD` date falls in, as its first day. */
export function monthOf(date: string): string {
  return `${date.slice(0, 7)}-01`;
}

/** The first day of the month `months` after `month` (before it, when negative). */
export function addMonths(month: string, months: number): string {
  const [year, monthNumber] = parts(month);
  return iso(new Date(Date.UTC(year, monthNumber - 1 + months, 1)));
}

/** The same day `months` months on, or the month's last day when it is shorter, e.g. 31 Jan → 28 Feb. */
export function shiftMonths(date: string, months: number): string {
  const [year, month, day] = parts(date);
  const lastDay = new Date(Date.UTC(year, month - 1 + months + 1, 0)).getUTCDate();
  return iso(new Date(Date.UTC(year, month - 1 + months, Math.min(day, lastDay))));
}

/** The Monday on or before a `YYYY-MM-DD` date. */
export function startOfWeek(date: string): string {
  const [year, month, day] = parts(date);
  const weekday = (new Date(Date.UTC(year, month - 1, day)).getUTCDay() + 6) % 7;
  return iso(new Date(Date.UTC(year, month - 1, day - weekday)));
}

/**
 * A month laid out as weeks from Monday to Sunday, each a row of seven `YYYY-MM-DD` dates, with
 * null for the days before the 1st and after the last day.
 */
export function monthWeeks(month: string): (string | null)[][] {
  const [year, monthNumber] = parts(month);
  const lead = (new Date(Date.UTC(year, monthNumber - 1, 1)).getUTCDay() + 6) % 7;
  const length = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  const cells: (string | null)[] = Array.from({ length: lead }, () => null);
  for (let day = 1; day <= length; day++) {
    cells.push(iso(new Date(Date.UTC(year, monthNumber - 1, day))));
  }
  while (cells.length % 7 !== 0) cells.push(null);
  const weeks: (string | null)[][] = [];
  for (let start = 0; start < cells.length; start += 7) weeks.push(cells.slice(start, start + 7));
  return weeks;
}
