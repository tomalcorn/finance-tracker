import { formatAmount, formatAmountCompact, parseAmount } from '@/theme/formatAmount';

describe('formatAmountCompact', () => {
  it('leaves off pence when there are none', () => {
    expect(formatAmountCompact(1200)).toBe('£1,200');
  });

  it('keeps pence when there are some', () => {
    expect(formatAmountCompact(1234.5)).toBe('£1,234.50');
  });
});

describe('parseAmount', () => {
  it.each([
    ['3.40', 3.4],
    ['£1,200', 1200],
    ['-2.5', -2.5],
    ['.5', 0.5],
    [' 12 ', 12],
  ])('reads %p as %p', (text, amount) => {
    expect(parseAmount(text)).toBe(amount);
  });

  it('reads a blank field as no amount', () => {
    expect(parseAmount('  ')).toBeNull();
  });

  it.each(['three', '1.2.3', '-'])('reads %p as not an amount', (text) => {
    expect(parseAmount(text)).toBeNaN();
  });
});

describe('formatAmount', () => {
  it('formats pounds with thousands separators and two decimal places', () => {
    expect(formatAmount(1234.5)).toBe('£1,234.50');
  });

  it('puts the minus sign before the pound sign', () => {
    expect(formatAmount(-10.99)).toBe('-£10.99');
  });
});
