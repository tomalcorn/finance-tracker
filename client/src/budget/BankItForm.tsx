import { useState } from 'react';

import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { CheckList } from '@/components/CheckList';
import { SelectField, type SelectOption } from '@/components/SelectField';
import type { CategoryView } from '@/domain/readModels';
import { formatAmount } from '@/theme/formatAmount';

type BankItFormProps = {
  /** The pots with something planned for this month. */
  pots: readonly CategoryView[];
  bankAccounts: readonly SelectOption[];
  /** Bank the chosen pots; rejects with a message to show when it can't. */
  onBank: (pots: CategoryView[], bankAccountId: string) => Promise<void>;
  onCancel: () => void;
};

/** Choose which pots to pay this month's plan into, and the account the money leaves. */
export function BankItForm({ pots, bankAccounts, onBank, onCancel }: BankItFormProps) {
  const [chosen, setChosen] = useState<string[]>(() => pots.map((pot) => pot.id));
  const [bankAccountId, setBankAccountId] = useState<string | null>(
    bankAccounts.length === 1 ? (bankAccounts[0]?.value ?? null) : null,
  );
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const banking = pots.filter((pot) => chosen.includes(pot.id));
  const total = banking.reduce((sum, pot) => sum + pot.budget, 0);

  if (pots.length === 0) {
    return (
      <>
        <AppText>Nothing to bank yet.</AppText>
        <AppText tone="muted">
          Give a pot an amount planned for this month first, then come back to pay it in.
        </AppText>
        <Button title="Close" variant="plain" onPress={onCancel} />
      </>
    );
  }

  if (bankAccounts.length === 0) {
    return (
      <>
        <AppText>You need a bank account to bank from.</AppText>
        <AppText tone="muted">
          Add one on the Streamlit app, then come back to bank your pots.
        </AppText>
        <Button title="Close" variant="plain" onPress={onCancel} />
      </>
    );
  }

  async function bank() {
    if (!bankAccountId) return;
    setSaving(true);
    setFailure(null);
    try {
      await onBank(banking, bankAccountId);
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error));
      setSaving(false);
    }
  }

  return (
    <>
      <CheckList
        label="Pots"
        options={pots.map((pot) => ({
          value: pot.id,
          label: pot.name,
          caption: `${formatAmount(pot.budget)} planned`,
        }))}
        selected={chosen}
        onChange={setChosen}
      />
      <SelectField
        label="From"
        value={bankAccountId}
        options={bankAccounts}
        onChange={setBankAccountId}
      />
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button
        title={banking.length > 0 ? `Bank ${formatAmount(total)}` : 'Bank'}
        onPress={() => void bank()}
        disabled={saving || banking.length === 0 || bankAccountId === null}
      />
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}
