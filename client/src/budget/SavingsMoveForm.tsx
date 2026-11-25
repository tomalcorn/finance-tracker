import { useState } from 'react';

import { AmountField } from '@/components/AmountField';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { DateField } from '@/components/DateField';
import { SelectField, type SelectOption } from '@/components/SelectField';
import { TextField } from '@/components/TextField';
import { today } from '@/domain/entities';
import { formatAmount, parseAmount } from '@/theme/formatAmount';
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
  const [amount, setAmount] = useState('');
  const [bankAccountId, setBankAccountId] = useState<string | null>(bankAccounts[0]?.value ?? null);
  const [paymentDate, setPaymentDate] = useState(today);
  const [name, setName] = useState('');
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const deposit = direction === 'deposit';

  if (bankAccounts.length === 0) {
    return (
      <>
        <AppText>You need a bank account to {deposit ? 'deposit from' : 'withdraw into'}.</AppText>
        <AppText tone="muted">
          Add one under Bank accounts on the overview, then come back to move your savings.
        </AppText>
        <Button title="Close" variant="plain" onPress={onCancel} />
      </>
    );
  }

  const parsed = parseAmount(amount);
  const amountError =
    parsed === null
      ? undefined
      : Number.isNaN(parsed)
        ? 'Enter an amount in pounds, e.g. 50.00.'
        : parsed <= 0
          ? 'Enter an amount above zero.'
          : undefined;
  const complete = parsed !== null && !amountError && bankAccountId !== null && paymentDate !== '';

  async function submit() {
    if (parsed === null || bankAccountId === null) return;
    setSaving(true);
    setFailure(null);
    try {
      await onSubmit({ direction, amount: parsed, bankAccountId, paymentDate, name });
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error));
      setSaving(false);
    }
  }

  const verb = deposit ? 'Deposit' : 'Withdraw';
  return (
    <>
      <AmountField label="Amount" value={amount} onChangeText={setAmount} error={amountError} />
      <SelectField
        label={deposit ? 'From' : 'Into'}
        value={bankAccountId}
        options={bankAccounts}
        onChange={setBankAccountId}
      />
      <DateField label="Date" value={paymentDate} onChange={setPaymentDate} />
      <TextField
        label="Name"
        value={name}
        onChangeText={setName}
        placeholder={deposit ? 'Savings deposit' : 'Savings withdrawal'}
      />
      <AppText variant="caption" tone="muted">
        {deposit
          ? 'Books one payment to Savings out of this account. Move the money into your savings at the same time.'
          : 'Books one negative payment to Savings, back into this account. Move the money out of your savings at the same time.'}
      </AppText>
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button
        title={complete && parsed !== null ? `${verb} ${formatAmount(parsed)}` : verb}
        onPress={() => void submit()}
        disabled={!complete || saving}
      />
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}
