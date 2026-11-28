import {
  amountError,
  formatAmount,
  formatAmountCompact,
  parseAmount,
  flipSign,
  type AmountSign,
} from '@/theme/formatAmount';

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

describe('flipSign', () => {
  it('makes a positive amount negative', () => {
    expect(flipSign('3.40')).toBe('-3.40');
  });

  it('makes a negative amount positive', () => {
    expect(flipSign('-3.40')).toBe('3.40');
  });

  it('turns a blank field into a minus, to type the amount after', () => {
    expect(flipSign('')).toBe('-');
    expect(flipSign('-')).toBe('');
  });

  it('ignores leading spaces', () => {
    expect(flipSign('  -2')).toBe('2');
  });
});

describe('amountError', () => {
  it.each<[AmountSign, string]>([
    ['positive', '0.01'],
    ['nonnegative', '0'],
    ['nonnegative', '12'],
    ['nonzero', '-3.40'],
    ['nonzero', '3.40'],
    ['any', '-3.40'],
    ['any', '0'],
  ])('lets a %s field take %p', (sign, text) => {
    expect(amountError(text, { sign })).toBeUndefined();
  });

  it.each<[AmountSign, string, string]>([
    ['positive', '0', 'Enter an amount above zero.'],
    ['positive', '-5', 'Enter an amount above zero.'],
    ['nonnegative', '-5', 'Enter an amount of 0 or more.'],
    ['nonzero', '0', 'An amount can’t be zero.'],
    ['nonzero', '-0', 'An amount can’t be zero.'],
  ])('stops a %s field taking %p', (sign, text, message) => {
    expect(amountError(text, { sign })).toBe(message);
  });

  it.each<AmountSign>(['positive', 'nonnegative', 'nonzero', 'any'])(
    'stops a %s field taking what isn’t an amount',
    (sign) => {
      expect(amountError('1.2.3', { sign })).toBe('Enter an amount in pounds, e.g. 12.50.');
    },
  );

  it.each<[AmountSign, string]>([
    ['positive', 'Enter the amount.'],
    ['nonzero', 'Enter the amount.'],
    ['nonnegative', 'Enter an amount, or 0.'],
    ['any', 'Enter an amount, or 0.'],
  ])('asks a %s field left blank for an amount', (sign, message) => {
    expect(amountError(' ', { sign })).toBe(message);
  });

  it.each<AmountSign>(['positive', 'nonnegative', 'nonzero', 'any'])(
    'lets an optional %s field be left blank',
    (sign) => {
      expect(amountError('', { sign, optional: true })).toBeUndefined();
    },
  );

  it('still checks an optional field that isn’t blank', () => {
    expect(amountError('0', { sign: 'positive', optional: true })).toBe(
      'Enter an amount above zero.',
    );
  });
});
