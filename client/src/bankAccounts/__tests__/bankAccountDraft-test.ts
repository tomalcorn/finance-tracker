import {
  bankAccountDraftErrors,
  bankAccountDraftOf,
  bankAccountRow,
} from '@/bankAccounts/bankAccountDraft';
import type { BankAccountView } from '@/domain/readModels';

const ACCOUNT: BankAccountView = {
  id: 'a',
  user_id: 'auth0|test',
  name: 'Monzo',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
  starting_balance: 1200.5,
  current_balance: 900,
};

describe('bankAccountDraftOf', () => {
  it('starts blank for a new account', () => {
    expect(bankAccountDraftOf(null)).toEqual({ name: '', startingBalance: '' });
  });

  it('holds an existing account’s fields', () => {
    expect(bankAccountDraftOf(ACCOUNT)).toEqual({ name: 'Monzo', startingBalance: '1200.50' });
  });
});

describe('bankAccountDraftErrors', () => {
  it('accepts a name and a balance', () => {
    expect(bankAccountDraftErrors({ name: 'Monzo', startingBalance: '10' })).toEqual({});
  });

  it('accepts a zero balance', () => {
    expect(bankAccountDraftErrors({ name: 'Monzo', startingBalance: '0' })).toEqual({});
  });

  it('accepts a balance below zero', () => {
    expect(bankAccountDraftErrors({ name: 'Amex', startingBalance: '-20' })).toEqual({});
  });

  it('needs a name', () => {
    expect(bankAccountDraftErrors({ name: ' ', startingBalance: '10' }).name).toBeDefined();
  });

  it('needs a balance', () => {
    const errors = bankAccountDraftErrors({ name: 'Monzo', startingBalance: '' });

    expect(errors.startingBalance).toBe('Enter the starting balance, or 0.');
  });

  it('refuses a balance that isn’t an amount', () => {
    const errors = bankAccountDraftErrors({ name: 'Monzo', startingBalance: 'lots' });

    expect(errors.startingBalance).toBe('Enter an amount in pounds, e.g. 1200.50.');
  });
});

describe('bankAccountRow', () => {
  it('builds a new account from the draft', () => {
    expect(bankAccountRow({ name: ' Monzo ', startingBalance: '£1,000' }, null)).toEqual({
      name: 'Monzo',
      starting_balance: 1000,
    });
  });

  it('keeps the id of the account being edited', () => {
    const row = bankAccountRow({ name: 'Monzo', startingBalance: '5' }, ACCOUNT);

    expect(row.id).toBe('a');
  });
});
