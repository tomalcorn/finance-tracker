import { useState } from 'react';

import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { CheckList } from '@/components/CheckList';
import { SelectField, type SelectOption } from '@/components/SelectField';
import { SheetNotice } from '@/components/SheetNotice';
import type { CategoryView } from '@/domain/readModels';
import { useSubmit } from '@/hooks/submit';
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
  const { submit, saving, failure } = useSubmit(onBank, { once: true });
  const banking = pots.filter((pot) => chosen.includes(pot.id));
  const total = banking.reduce((sum, pot) => sum + pot.budget, 0);

  if (pots.length === 0) {
    return (
      <SheetNotice
        message="Nothing to bank yet."
        detail="Give a pot an amount planned for this month first, then come back to pay it in."
        onClose={onCancel}
      />
    );
  }

  if (bankAccounts.length === 0) {
    return (
      <SheetNotice
        message="You need a bank account to bank from."
        detail="Add one under Bank accounts on the overview, then come back to bank your pots."
        onClose={onCancel}
      />
    );
  }

  function bank() {
    if (bankAccountId) void submit(banking, bankAccountId);
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
      <AppText variant="caption" tone="muted">
        Books one payment per pot out of this account. Move the money into your savings at the same
        time.
      </AppText>
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button
        title={banking.length > 0 ? `Bank ${formatAmount(total)}` : 'Bank'}
        onPress={bank}
        disabled={saving || banking.length === 0 || bankAccountId === null}
      />
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}
