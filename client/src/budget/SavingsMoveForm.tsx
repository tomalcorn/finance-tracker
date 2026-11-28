import { useState } from 'react';

import {
  SAVINGS_MOVE_NAMES,
  savingsMoveDraftErrors,
  savingsMoveDraftOf,
  savingsMoveOf,
} from '@/budget/savingsMoveDraft';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { DateField } from '@/components/DateField';
import { SelectField, type SelectOption } from '@/components/SelectField';
import { SheetNotice } from '@/components/SheetNotice';
import { TextField } from '@/components/TextField';
import { today } from '@/domain/entities';
import { useSubmit } from '@/hooks/submit';
import { formatAmount } from '@/theme/formatAmount';
import type { SavingsDirection, SavingsMove } from '@/useCases/moveSavings';

type SavingsMoveFormProps = {
  direction: SavingsDirection;
  bankAccounts: readonly SelectOption[];
  /** Move the money; rejects with a message to show when it can't. */
  onSubmit: (move: SavingsMove) => Promise<void>;
  onCancel: () => void;
};

/** How much to move into or out of savings, the account on the other side, and when. */
export function SavingsMoveForm({
  direction,
  bankAccounts,
  onSubmit,
  onCancel,
}: SavingsMoveFormProps) {
  const [draft, setDraft] = useState(() => savingsMoveDraftOf(today(), bankAccounts));
  const { submit, saving, failure } = useSubmit(onSubmit, { once: true });
  const deposit = direction === 'deposit';

  if (bankAccounts.length === 0) {
    return (
      <SheetNotice
        message={`You need a bank account to ${deposit ? 'deposit from' : 'withdraw into'}.`}
        detail="Add one under Bank accounts on the overview, then come back to move your savings."
        onClose={onCancel}
      />
    );
  }

  const errors = savingsMoveDraftErrors(draft);
  const move = savingsMoveOf(draft, direction);

  const verb = deposit ? 'Deposit' : 'Withdraw';
  return (
    <>
      <TextField
        label="Amount"
        value={draft.amount}
        onChangeText={(amount) => setDraft((current) => ({ ...current, amount }))}
        inputMode="decimal"
        placeholder="0.00"
        error={errors.amount}
      />
      <SelectField
        label={deposit ? 'From' : 'Into'}
        value={draft.bankAccountId}
        options={bankAccounts}
        onChange={(bankAccountId) => setDraft((current) => ({ ...current, bankAccountId }))}
        error={errors.bankAccountId}
      />
      <DateField
        label="Date"
        value={draft.date}
        onChange={(date) => setDraft((current) => ({ ...current, date }))}
        error={errors.date}
      />
      <TextField
        label="Name"
        value={draft.name}
        onChangeText={(name) => setDraft((current) => ({ ...current, name }))}
        placeholder={SAVINGS_MOVE_NAMES[direction]}
      />
      <AppText variant="caption" tone="muted">
        {deposit
          ? 'Books one payment to Savings out of this account. Move the money into your savings at the same time.'
          : 'Books one negative payment to Savings, back into this account. Move the money out of your savings at the same time.'}
      </AppText>
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button
        title={move ? `${verb} ${formatAmount(move.amount)}` : verb}
        onPress={() => {
          if (move) void submit(move);
        }}
        disabled={!move || saving}
      />
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}
