import type { PaymentView } from '@/domain/readModels';
import {
  matchesSearch,
  parseSearch,
  paymentSearchFields,
  searchSuggestions,
} from '@/payments/paymentSearch';

const LABELS: Record<string, string> = {
  amex: 'AMEX',
  amexGold: 'AMEX Gold',
  santander: 'Santander',
  expenses: 'Expenses',
  travel: 'Expenses - Travel',
  savings: 'Savings',
};

const FIELDS = paymentSearchFields({
  names: ['Coffee', 'AMEX cashback'],
  bankAccounts: ['AMEX', 'AMEX Gold', 'Santander'],
  categories: ['Expenses', 'Expenses - Travel', 'Savings'],
  incomeSources: ['Salary'],
  labelOf: (id) => LABELS[id],
});

function payment(overrides: Partial<PaymentView> = {}): PaymentView {
  return {
    id: 'id',
    user_id: 'auth0|test',
    name: 'Coffee',
    _created_at: '2026-10-01T09:30:12.345678+00:00',
    ownership_type: 'personal',
    joint_account_id: null,
    payment_date: '2026-11-01',
    payment_type: 'expense',
    expense: 3,
    income: 0,
    checked: false,
    bank_account_id: 'amex',
    category_id: 'travel',
    income_source_id: null,
    subscription_id: null,
    linked_payment_id: null,
    ...overrides,
  };
}

/** Whether a payment is found by a search, described by its account's name. */
function finds(row: PaymentView, query: string): boolean {
  return matchesSearch(row, parseSearch(query, FIELDS), (it) => LABELS[it.bank_account_id] ?? '');
}

function suggested(query: string): string[] {
  return searchSuggestions(query, FIELDS).map((suggestion) => suggestion.label);
}

describe('parseSearch', () => {
  it('keeps plain words as text', () => {
    expect(parseSearch('Coffee Shop', FIELDS)).toEqual({ text: 'coffee shop', filters: [] });
  });

  it('reads a filter', () => {
    expect(parseSearch('@account:AMEX', FIELDS).filters).toEqual([
      { field: expect.objectContaining({ key: 'account' }), value: 'amex' },
    ]);
  });

  it('reads a value with spaces, without quotes', () => {
    expect(parseSearch('@category:Expenses - Travel', FIELDS).filters[0]?.value).toBe(
      'expenses - travel',
    );
  });

  it('leaves the words after a value as text', () => {
    expect(parseSearch('@account:AMEX coffee', FIELDS).text).toBe('coffee');
  });

  it('keeps the words before a filter as text', () => {
    expect(parseSearch('coffee @account:AMEX', FIELDS).text).toBe('coffee');
  });

  it('reads several filters', () => {
    expect(parseSearch('@account:AMEX @type:out', FIELDS).filters.map((it) => it.value)).toEqual([
      'amex',
      'out',
    ]);
  });

  it('asks for nothing while a filter is half typed', () => {
    expect(parseSearch('@acc', FIELDS)).toEqual({ text: '', filters: [] });
  });

  it('asks for nothing before a value is typed', () => {
    expect(parseSearch('@account:', FIELDS)).toEqual({ text: '', filters: [] });
  });

  it('treats an @word that isn’t a field as text', () => {
    expect(parseSearch('@home', FIELDS).text).toBe('@home');
  });

  it('treats an unknown field as text', () => {
    expect(parseSearch('@colour:red', FIELDS).text).toBe('@colour:red');
  });

  it('treats an @ inside a word as text', () => {
    expect(parseSearch('me@account:x', FIELDS).text).toBe('me@account:x');
  });
});

describe('matchesSearch', () => {
  it('finds text in the name', () => {
    expect(finds(payment(), 'coff')).toBe(true);
  });

  it('finds text in the description', () => {
    expect(finds(payment(), 'amex')).toBe(true);
  });

  it('finds an account’s name in another account’s payment name, as plain text', () => {
    expect(finds(payment({ name: 'AMEX cashback', bank_account_id: 'santander' }), 'amex')).toBe(
      true,
    );
  });

  it('ignores the payment’s name when filtering by account', () => {
    expect(
      finds(payment({ name: 'AMEX cashback', bank_account_id: 'santander' }), '@account:amex'),
    ).toBe(false);
  });

  it('means exactly the account named, not one containing it', () => {
    expect(finds(payment({ bank_account_id: 'amexGold' }), '@account:AMEX')).toBe(false);
  });

  it('looks inside the value when no option is named', () => {
    expect(finds(payment({ bank_account_id: 'amexGold' }), '@account:gold')).toBe(true);
  });

  it('takes in a tracker’s subcategories', () => {
    expect(finds(payment(), '@category:Expenses')).toBe(true);
  });

  it('doesn’t match a payment with no value for the field', () => {
    expect(finds(payment({ category_id: null }), '@category:Expenses')).toBe(false);
  });

  it('needs every filter to match', () => {
    expect(finds(payment(), '@account:AMEX @type:in')).toBe(false);
  });

  it('needs the text to match as well', () => {
    expect(finds(payment(), '@account:AMEX lunch')).toBe(false);
  });

  it('filters on whether it is ticked', () => {
    expect(finds(payment({ checked: true }), '@checked:yes')).toBe(true);
  });

  it('filters on the name alone', () => {
    expect(finds(payment({ name: 'Lunch' }), '@name:amex')).toBe(false);
  });
});

describe('searchSuggestions', () => {
  it('offers nothing for plain text', () => {
    expect(suggested('coffee')).toEqual([]);
  });

  it('offers every field after @', () => {
    expect(suggested('@')).toEqual([
      '@account:',
      '@category:',
      '@source:',
      '@name:',
      '@type:',
      '@checked:',
    ]);
  });

  it('narrows the fields as they are typed', () => {
    expect(suggested('@ac')).toEqual(['@account:']);
  });

  it('completes a field, keeping what came before', () => {
    expect(searchSuggestions('coffee @ac', FIELDS)[0]?.query).toBe('coffee @account:');
  });

  it('offers a field’s values after the colon', () => {
    expect(suggested('@account:')).toEqual(['AMEX', 'AMEX Gold', 'Santander']);
  });

  it('narrows the values as they are typed', () => {
    expect(suggested('@account:san')).toEqual(['Santander']);
  });

  it('completes a value, ready for what comes next', () => {
    expect(searchSuggestions('@account:san', FIELDS)[0]?.query).toBe('@account:Santander ');
  });

  it('still offers longer values once one is named', () => {
    expect(suggested('@account:AMEX')).toEqual(['AMEX', 'AMEX Gold']);
  });

  it('offers nothing once the only value is typed in full', () => {
    expect(suggested('@account:Santander')).toEqual([]);
  });

  it('offers nothing once a value is chosen', () => {
    expect(suggested('@account:AMEX ')).toEqual([]);
  });

  it('offers nothing for an unknown field', () => {
    expect(suggested('@colour:')).toEqual([]);
  });
});
