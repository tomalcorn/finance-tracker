import { formatAmount, parseAmount } from '@/theme/formatAmount';

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
