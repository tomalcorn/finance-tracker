import type { QuickButtonView } from '@/domain/readModels';
import {
  draftErrors,
  draftOf,
  draftRow,
  nextPosition,
  ordered,
  type ButtonDraft,
} from '@/quickExpenses/buttonDraft';

const BANK_ACCOUNT_ID = '0c4e7a2d-1b5f-4e8a-a3c6-9d2f8b1e4a07';

const BUTTON: QuickButtonView = {
  id: '5f2b1c9e-8d3a-4b6f-9e1d-2c7a4b8e6f01',
  user_id: 'auth0|65f0c2a1b3d4e5f6a7b8c9d0',
  name: 'Coffee',
  _created_at: '2026-10-01T09:30:12.345678+00:00',
  ownership_type: 'personal',
  joint_account_id: null,
  mode: 'log',
  payment_name: null,
  expense: 3.4,
  bank_account_id: BANK_ACCOUNT_ID,
  category_id: null,
  icon: '☕',
  display_order: 2,
};

const LOG_DRAFT: ButtonDraft = {
  name: 'Coffee',
  icon: '',
  mode: 'log',
  paymentName: '',
  amount: '3.40',
  bankAccountId: BANK_ACCOUNT_ID,
  categoryId: null,
  position: '0',
};

describe('draftErrors', () => {
  it('accepts a complete log button', () => {
    expect(draftErrors(LOG_DRAFT)).toEqual({});
  });

  it('needs a name', () => {
    expect(draftErrors({ ...LOG_DRAFT, name: '  ' })).toHaveProperty('name');
  });

  it('needs an amount and a bank account on a button that logs at once', () => {
    expect(Object.keys(draftErrors({ ...LOG_DRAFT, amount: '', bankAccountId: null }))).toEqual([
      'amount',
      'bankAccountId',
    ]);
  });

  it('needs only a name on a button that asks first', () => {
    expect(draftErrors({ ...LOG_DRAFT, mode: 'prompt', amount: '', bankAccountId: null })).toEqual(
      {},
    );
  });

  it('refuses an amount of zero', () => {
    expect(draftErrors({ ...LOG_DRAFT, amount: '0.00' })).toHaveProperty('amount');
  });

  it('allows a negative amount', () => {
    expect(draftErrors({ ...LOG_DRAFT, amount: '-2.50' })).toEqual({});
  });

  it('refuses an amount that isn’t one', () => {
    expect(draftErrors({ ...LOG_DRAFT, amount: 'three' })).toHaveProperty('amount');
  });

  it('refuses a position that isn’t a whole number', () => {
    expect(draftErrors({ ...LOG_DRAFT, position: '1.5' })).toHaveProperty('position');
  });
});

describe('draftRow', () => {
  it('keeps the edited button’s id', () => {
    expect(draftRow(LOG_DRAFT, BUTTON).id).toBe(BUTTON.id);
  });

  it('saves blank optional fields as null', () => {
    expect(draftRow({ ...LOG_DRAFT, mode: 'prompt', amount: '', icon: ' ' }, null)).toMatchObject({
      expense: null,
      icon: null,
      payment_name: null,
    });
  });

  it('reads the amount and position as numbers', () => {
    expect(draftRow({ ...LOG_DRAFT, amount: '£1,200', position: '3' }, null)).toMatchObject({
      expense: 1200,
      display_order: 3,
    });
  });
});

describe('draftOf', () => {
  it('fills the form from the button being edited', () => {
    expect(draftOf(BUTTON, 0)).toMatchObject({ name: 'Coffee', amount: '3.40', position: '2' });
  });

  it('places a new button where it is told', () => {
    expect(draftOf(null, 5).position).toBe('5');
  });
});

describe('ordering', () => {
  it('orders buttons by position, then by name', () => {
    const buttons = [
      { ...BUTTON, name: 'Tea', display_order: 1 },
      { ...BUTTON, name: 'Bus', display_order: 1 },
      { ...BUTTON, name: 'Lunch', display_order: 0 },
    ];

    expect(ordered(buttons).map((button) => button.name)).toEqual(['Lunch', 'Bus', 'Tea']);
  });

  it('puts a new button after the last one', () => {
    expect(nextPosition([BUTTON, { ...BUTTON, display_order: 7 }])).toBe(8);
  });

  it('puts the first button at 0', () => {
    expect(nextPosition([])).toBe(0);
  });
});
