import { formatAmountCompact } from '@/theme/formatAmount';
import { formatDayOfMonth, formatMonthShort } from '@/theme/formatDate';

/** A labelled position along the date axis. */
export type DateTick = { index: number; label: string };

/** Roughly how many gaps the value axis is divided into. */
const VALUE_GAPS = 3;

/** Where the axis of a series flat at zero reaches, having no size of its own to go by. */
const FLAT_AT_ZERO_TOP = 100;

/** The size of gap between value ticks that is round and closest to dividing `range` evenly. */
function roundStep(range: number): number {
  const rough = range / VALUE_GAPS;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  const multiple = [1, 2, 2.5, 5, 10].find((candidate) => candidate * magnitude >= rough) ?? 10;
  return Math.max(multiple * magnitude, 0.01);
}

/**
 * Pick round ticks for the value axis, lowest first, spanning every value. A series that never
 * moves is measured from zero, so its axis still means something.
 */
export function valueTicks(values: readonly number[]): number[] {
  const lowest = Math.min(...values);
  const highest = Math.max(...values);
  const flat = lowest === highest;
  const low = flat ? Math.min(lowest, 0) : lowest;
  const high = !flat ? highest : lowest === 0 ? FLAT_AT_ZERO_TOP : Math.max(highest, 0);
  const step = roundStep(high - low);
  const first = Math.floor(low / step);
  const last = Math.ceil(high / step);
  return Array.from(
    { length: last - first + 1 },
    // Adding zero turns a -0 into a 0, which would otherwise be labelled `-£0`.
    (_, index) => Math.round((first + index) * step * 100) / 100 + 0,
  );
}

/** Label a value tick in pounds, compacted from £10,000 so a large axis stays narrow. */
export function formatValueTick(value: number): string {
  if (Math.abs(value) < 10_000) return formatAmountCompact(value);
  return `${value < 0 ? '-' : ''}£${Math.abs(value) / 1000}K`;
}

/**
 * Pick the ticks for the date axis: the first of each month, or just both ends for a span too short
 * to reach two of them.
 */
export function dateTicks(dates: readonly string[]): DateTick[] {
  const months = dates.flatMap((date, index) =>
    date.endsWith('-01') ? [{ index, label: formatMonthShort(date) }] : [],
  );
  if (months.length >= 2) return months;
  const lastIndex = dates.length - 1;
  return [0, lastIndex].map((index) => ({
    index,
    label: formatDayOfMonth(dates[index] ?? ''),
  }));
}

/** Find the series position closest to a distance along a plot, for following a pointer. */
export function nearestIndex(x: number, plotWidth: number, count: number): number {
  const lastIndex = count - 1;
  const index = Math.round((x / plotWidth) * lastIndex);
  return Math.min(Math.max(index, 0), lastIndex);
}
