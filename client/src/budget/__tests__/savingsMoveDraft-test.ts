import {
  savingsMoveDraftErrors,
  savingsMoveDraftOf,
  savingsMoveOf,
  type SavingsMoveDraft,
} from '@/budget/savingsMoveDraft';

const CURRENT = { value: 'current', label: 'Current' };
const EVERYDAY = { value: 'everyday', label: 'Everyday' };

function draft(overrides: Partial<SavingsMoveDraft> = {}): SavingsMoveDraft {
  return {
    amount: '50',
    bankAccountId: 'current',
    date: '2026-11-01',
    name: '',
    ...overrides,
  };
}

describe('savingsMoveDraftOf', () => {
  it('starts on the date given', () => {
    expect(savingsMoveDraftOf('2026-11-01', [CURRENT]).date).toBe('2026-11-01');
  });

  it('chooses the first account', () => {
    expect(savingsMoveDraftOf('2026-11-01', [CURRENT, EVERYDAY]).bankAccountId).toBe('current');
  });

  it('chooses no account when there is none', () => {
    expect(savingsMoveDraftOf('2026-11-01', []).bankAccountId).toBeNull();
  });
});

describe('savingsMoveDraftErrors', () => {
  it('finds nothing wrong with a complete draft', () => {
    expect(savingsMoveDraftErrors(draft())).toEqual({});
  });

  it('finds nothing wrong with an amount not typed yet', () => {
    expect(savingsMoveDraftErrors(draft({ amount: '' }))).toEqual({});
  });

  it.each([
    ['an amount that isn’t one', { amount: 'lots' }, 'amount'],
    ['a zero amount', { amount: '0' }, 'amount'],
    ['a negative amount', { amount: '-20' }, 'amount'],
    ['no account', { bankAccountId: null }, 'bankAccountId'],
    ['a date that isn’t one', { date: '2026-13-01' }, 'date'],
  ])('flags %s', (_case, overrides, field) => {
    expect(Object.keys(savingsMoveDraftErrors(draft(overrides)))).toEqual([field]);
  });
});

describe('savingsMoveOf', () => {
  it('reads a valid draft', () => {
    expect(savingsMoveOf(draft({ amount: '£1,200.50', name: 'Bonus' }), 'deposit')).toEqual({
      direction: 'deposit',
      amount: 1200.5,
      bankAccountId: 'current',
      paymentDate: '2026-11-01',
      name: 'Bonus',
    });
  });

  it('trims the name typed', () => {
    expect(savingsMoveOf(draft({ name: '  Bonus  ' }), 'deposit')?.name).toBe('Bonus');
  });

  it.each([
    ['deposit', 'Savings deposit'],
    ['withdraw', 'Savings withdrawal'],
  ] as const)('names a %s with no name typed %p', (direction, name) => {
    expect(savingsMoveOf(draft({ name: '   ' }), direction)?.name).toBe(name);
  });

  it('gives nothing before an amount is typed', () => {
    expect(savingsMoveOf(draft({ amount: '' }), 'deposit')).toBeNull();
  });

  it('gives nothing for a draft with a problem', () => {
    expect(savingsMoveOf(draft({ amount: '-20' }), 'withdraw')).toBeNull();
  });
});
