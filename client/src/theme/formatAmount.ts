const GBP = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' });

/** Format an amount of money in pounds, e.g. `-£1,234.50`. */
export function formatAmount(value: number): string {
  return GBP.format(value);
}
