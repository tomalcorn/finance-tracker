import { formatAmount } from '@/theme/formatAmount';

describe('formatAmount', () => {
  it('formats pounds with thousands separators and two decimal places', () => {
    expect(formatAmount(1234.5)).toBe('£1,234.50');
  });

  it('puts the minus sign before the pound sign', () => {
    expect(formatAmount(-10.99)).toBe('-£10.99');
  });
});
