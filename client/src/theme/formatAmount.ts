const GBP = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });

/** Format an amount of money in pounds, e.g. `-£1,234.50`. */
export function formatAmount(value: number): string {
  return GBP.format(value);
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
