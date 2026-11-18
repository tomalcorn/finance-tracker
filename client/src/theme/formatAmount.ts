const GBP = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });
const WHOLE_GBP = new Intl.NumberFormat('en-GB', {
  style: 'currency',
  currency: 'GBP',
  maximumFractionDigits: 0,
});

/** Format an amount of money in pounds, e.g. `-£1,234.50`. */
export function formatAmount(value: number): string {
  return GBP.format(value);
}

/** Format an amount in pounds, leaving off the pence when there are none, e.g. `£1,200`. */
export function formatAmountCompact(value: number): string {
  return Number.isInteger(value) ? WHOLE_GBP.format(value) : GBP.format(value);
}

/**
 * Read an amount typed in pounds, e.g. `3.40`, `£1,200` or `-2.5`.
 *
 * @returns The amount, `null` for a blank field, or `NaN` when it isn't an amount.
 */
export function parseAmount(text: string): number | null {
  const cleaned = text.replace(/[£,\s]/g, '');
  if (cleaned === '') return null;
  return /^-?(\d+\.?\d*|\.\d+)$/.test(cleaned) ? Number(cleaned) : NaN;
}

/**
 * Flip the sign of an amount as typed, e.g. `3.40` to `-3.40` and back. A blank field becomes `-`,
 * so the sign can be chosen before the amount is typed.
 */
export function flipSign(text: string): string {
  const trimmed = text.trimStart();
  return trimmed.startsWith('-') ? trimmed.slice(1) : `-${trimmed}`;
}
