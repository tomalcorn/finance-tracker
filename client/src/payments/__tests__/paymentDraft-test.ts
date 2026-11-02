import type { PaymentView } from '@/domain/readModels';
import {
  paymentDraftErrors,
  paymentDraftOf,
  paymentRow,
  type PaymentDraft,
} from '@/payments/paymentDraft';

const SALARY: PaymentView = {
  id: '4d5e6f70-0000-4000-8000-000000000001',
  user_id: 'auth0|test',
  name: 'Salary',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
  payment_date: '2026-10-28',
  payment_type: 'income',
  expense: 0,
  income: 2500,
  checked: true,
  bank_account_id: 'bank',
  category_id: null,
  income_source_id: 'salary-source',
  subscription_id: null,
  linked_payment_id: null,
};

const DRAFT: PaymentDraft = {
  type: 'expense',
  name: 'Coffee',
  amount: '3.40',
  date: '2026-11-01',
  bankAccountId: 'bank',
  sourceId: 'groceries',
  checked: false,
};

describe('paymentDraftOf', () => {
  it('starts a new payment as an expense on the given date', () => {
    expect(paymentDraftOf(null, '2026-11-01')).toEqual({
      type: 'expense',
      name: '',
      amount: '',
      date: '2026-11-01',
      bankAccountId: null,
      sourceId: null,
      checked: false,
    });
  });

  it('fills an income in from its amount in and income source', () => {
    expect(paymentDraftOf(SALARY, '2026-11-01')).toEqual({
      type: 'income',
      name: 'Salary',
      amount: '2500.00',
      date: '2026-10-28',
      bankAccountId: 'bank',
      sourceId: 'salary-source',
      checked: true,
    });
  });
});

describe('paymentDraftErrors', () => {
  it('passes a complete draft', () => {
    expect(paymentDraftErrors(DRAFT)).toEqual({});
  });

  it('asks for a name', () => {
    expect(paymentDraftErrors({ ...DRAFT, name: ' ' })).toEqual({ name: 'Give it a name.' });
  });

  it('asks for an amount', () => {
    expect(paymentDraftErrors({ ...DRAFT, amount: '' })).toEqual({ amount: 'Enter the amount.' });
  });

  it('refuses an amount of zero', () => {
    expect(paymentDraftErrors({ ...DRAFT, amount: '0' })).toEqual({
      amount: 'An amount can’t be zero.',
    });
  });

  it('allows a negative amount, for money coming back', () => {
    expect(paymentDraftErrors({ ...DRAFT, amount: '-3.40' })).toEqual({});
  });

  it('refuses a date that doesn’t exist', () => {
    expect(paymentDraftErrors({ ...DRAFT, date: '2026-02-30' })).toEqual({
      date: 'Enter a date, e.g. 2026-11-01.',
    });
  });

  it('asks for a bank account', () => {
    expect(paymentDraftErrors({ ...DRAFT, bankAccountId: null })).toEqual({
      bankAccountId: 'Choose the account it moved through.',
    });
  });
});

describe('paymentRow', () => {
  it('books an expense’s amount out, against its category', () => {
    expect(paymentRow(DRAFT, null)).toEqual({
      payment_type: 'expense',
      name: 'Coffee',
      payment_date: '2026-11-01',
      expense: 3.4,
      income: 0,
      bank_account_id: 'bank',
      category_id: 'groceries',
      income_source_id: null,
      checked: false,
    });
  });

  it('keeps the edited payment’s other columns', () => {
    const row = paymentRow({ ...DRAFT, type: 'income', sourceId: 'salary-source' }, SALARY);

    expect(row).toEqual(
      expect.objectContaining({ id: SALARY.id, income: 3.4, expense: 0, category_id: null }),
    );
  });
});
