import {
  contributionDraftErrors,
  contributionDraftOf,
  contributionOf,
  type ContributionDraft,
} from '@/contributions/contributionDraft';

const OPTION = { value: 'only', label: 'Only' };
const OTHER = { value: 'other', label: 'Other' };

function draft(overrides: Partial<ContributionDraft> = {}): ContributionDraft {
  return {
    amount: '150',
    date: '2026-11-01',
    fromBankAccountId: 'from',
    toBankAccountId: 'to',
    incomeSourceId: 'source',
    ...overrides,
  };
}

describe('contributionDraftOf', () => {
  it('starts on the date given', () => {
    expect(contributionDraftOf('2026-11-01', [], [], []).date).toBe('2026-11-01');
  });

  it('makes a choice with only one option', () => {
    expect(contributionDraftOf('2026-11-01', [OPTION], [], []).fromBankAccountId).toBe('only');
  });

  it('leaves a choice with several options', () => {
    expect(contributionDraftOf('2026-11-01', [], [OPTION, OTHER], []).toBankAccountId).toBeNull();
  });
});

describe('contributionDraftErrors', () => {
  it('finds nothing wrong with a complete draft', () => {
    expect(contributionDraftErrors(draft())).toEqual({});
  });

  it.each([
    ['a blank amount', { amount: '' }, 'amount'],
    ['an amount that isn’t one', { amount: 'lots' }, 'amount'],
    ['a zero amount', { amount: '0' }, 'amount'],
    ['a negative amount', { amount: '-5' }, 'amount'],
    ['a date that isn’t one', { date: '2026-13-01' }, 'date'],
    ['no account to leave', { fromBankAccountId: null }, 'fromBankAccountId'],
    ['no account to arrive in', { toBankAccountId: null }, 'toBankAccountId'],
    ['no income source', { incomeSourceId: null }, 'incomeSourceId'],
  ])('flags %s', (_case, overrides, field) => {
    expect(Object.keys(contributionDraftErrors(draft(overrides)))).toEqual([field]);
  });
});

describe('contributionOf', () => {
  it('reads a valid draft', () => {
    expect(contributionOf(draft({ amount: '£1,200.50' }))).toEqual({
      amount: 1200.5,
      fromBankAccountId: 'from',
      toBankAccountId: 'to',
      incomeSourceId: 'source',
      paymentDate: '2026-11-01',
    });
  });

  it('gives nothing for a draft with a problem', () => {
    expect(contributionOf(draft({ amount: '0' }))).toBeNull();
  });
});
