import { useState } from 'react';

import {
  bankAccountDraftErrors,
  bankAccountDraftOf,
  type BankAccountDraft,
} from '@/bankAccounts/bankAccountDraft';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { TextField } from '@/components/TextField';
import type { BankAccountView } from '@/domain/readModels';
import { formatAmount } from '@/theme/formatAmount';

type BankAccountFormProps = {
  /** The account being edited, or null to add one. */
  account: BankAccountView | null;
  /** How many quick buttons log to it, which go too if it is deleted. */
  quickButtons?: number;
  /** Save the draft; rejects with a message to show when it can't. */
  onSave: (draft: BankAccountDraft) => Promise<void>;
  /**
   * Delete the account being edited; rejects with a message to show when it can't. Left out while it
   * can't be deleted, because the database refuses while payments or subscriptions use it.
   */
  onDelete?: () => Promise<void>;
  /** Offers a way out, where the form isn't simply left behind. */
  onCancel?: () => void;
};

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** A bank account's name and starting balance. Delete asks to be confirmed. */
export function BankAccountForm({
  account,
  quickButtons = 0,
  onSave,
  onDelete,
  onCancel,
}: BankAccountFormProps) {
  const [draft, setDraft] = useState(() => bankAccountDraftOf(account));
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const errors = touched ? bankAccountDraftErrors(draft) : {};

  async function run(action: () => Promise<void>) {
    setSaving(true);
    setFailure(null);
    try {
      await action();
    } catch (error) {
      setFailure(messageOf(error));
    } finally {
      setSaving(false);
    }
  }

  function save() {
    setTouched(true);
    if (Object.keys(bankAccountDraftErrors(draft)).length > 0) return;
    void run(() => onSave(draft));
  }

  if (confirmingDelete && account && onDelete) {
    return (
      <>
        <AppText>Delete “{account.name}”?</AppText>
        {quickButtons > 0 ? (
          <AppText tone="muted">
            {quickButtons === 1
              ? 'The quick button that logs to it goes too.'
              : `The ${quickButtons} quick buttons that log to it go too.`}
          </AppText>
        ) : null}
        {failure ? <AppText tone="negative">{failure}</AppText> : null}
        <Button
          title="Delete"
          variant="destructive"
          onPress={() => void run(onDelete)}
          disabled={saving}
        />
        <Button title="Keep it" variant="plain" onPress={() => setConfirmingDelete(false)} />
      </>
    );
  }

  return (
    <>
      <TextField
        label="Name"
        value={draft.name}
        onChangeText={(name) => setDraft((current) => ({ ...current, name }))}
        placeholder="e.g. Monzo"
        error={errors.name}
      />
      <TextField
        label="Starting balance"
        value={draft.startingBalance}
        onChangeText={(startingBalance) => setDraft((current) => ({ ...current, startingBalance }))}
        inputMode="decimal"
        placeholder="0.00"
        error={errors.startingBalance}
      />
      <AppText variant="caption" tone="muted">
        {account
          ? `What was in it when you started tracking. Its current balance, ${formatAmount(account.current_balance)}, is this plus every payment up to today.`
          : 'What was in it when you started tracking, below zero if you owed money on it.'}
      </AppText>
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button title={account ? 'Save' : 'Add'} onPress={save} disabled={saving} />
      {account && onDelete ? (
        <Button title="Delete" variant="destructive" onPress={() => setConfirmingDelete(true)} />
      ) : null}
      {account && !onDelete ? (
        <AppText variant="caption" tone="muted">
          It can’t be deleted while payments or subscriptions use it.
        </AppText>
      ) : null}
      {onCancel ? <Button title="Cancel" variant="plain" onPress={onCancel} /> : null}
    </>
  );
}
