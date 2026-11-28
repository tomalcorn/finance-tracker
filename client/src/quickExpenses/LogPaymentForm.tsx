import { useState } from 'react';

import { AmountField } from '@/components/AmountField';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import type { SelectOption } from '@/components/SelectField';
import { SelectField } from '@/components/SelectField';
import { TextField } from '@/components/TextField';
import type { QuickButtonView } from '@/domain/readModels';
import { useSubmit } from '@/hooks/submit';
import { amountError, parseAmount } from '@/theme/formatAmount';
import { presetPayment, type PaymentOverrides } from '@/useCases/logQuickPayment';

type LogPaymentFormProps = {
  button: QuickButtonView;
  bankAccounts: readonly SelectOption[];
  categories: readonly SelectOption[];
  /** Log the payment; rejects with a message to show when it can't. */
  onSubmit: (overrides: PaymentOverrides) => Promise<void>;
  onCancel: () => void;
};

/** The form behind a button that asks first: its preset, filled in, to complete and log. */
export function LogPaymentForm({
  button,
  bankAccounts,
  categories,
  onSubmit,
  onCancel,
}: LogPaymentFormProps) {
  const preset = presetPayment(button);
  const [name, setName] = useState(preset.name);
  const [amount, setAmount] = useState(preset.expense === null ? '' : preset.expense.toFixed(2));
  const [bankAccountId, setBankAccountId] = useState(preset.bank_account_id);
  const [categoryId, setCategoryId] = useState(preset.category_id);
  const { submit, saving, failure } = useSubmit(onSubmit, { once: true });

  const expense = parseAmount(amount);
  const amountProblem = amountError(amount, { sign: 'nonzero', optional: true });
  const complete =
    name.trim() !== '' && expense !== null && !amountProblem && bankAccountId !== null;

  return (
    <>
      <TextField label="Name" value={name} onChangeText={setName} placeholder="e.g. Coffee" />
      <AmountField label="Amount" value={amount} onChangeText={setAmount} error={amountProblem} />
      <SelectField
        label="Bank account"
        value={bankAccountId}
        options={bankAccounts}
        onChange={setBankAccountId}
      />
      <SelectField
        label="Category"
        value={categoryId}
        options={categories}
        onChange={setCategoryId}
        noneLabel="None"
      />
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button
        title="Log payment"
        onPress={() =>
          void submit({
            name: name.trim(),
            expense,
            bank_account_id: bankAccountId,
            category_id: categoryId,
          })
        }
        disabled={!complete || saving}
      />
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}
