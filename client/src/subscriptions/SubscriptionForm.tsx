import { useState } from 'react';

import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { DateField } from '@/components/DateField';
import { SelectField, type SelectOption } from '@/components/SelectField';
import { SwitchField } from '@/components/SwitchField';
import { TextField } from '@/components/TextField';
import type { Cadence } from '@/domain/entities';
import type { SubscriptionView } from '@/domain/readModels';
import {
  CADENCES,
  subscriptionDraftErrors,
  type SubscriptionDraft,
} from '@/subscriptions/subscriptionDraft';

type SubscriptionFormProps = {
  /** The subscription being edited, or null to add one. */
  subscription: SubscriptionView | null;
  initial: SubscriptionDraft;
  /** Ask for the joint account and income source rather than a category. */
  contribution: boolean;
  bankAccounts: readonly SelectOption[];
  categories: readonly SelectOption[];
  jointBankAccounts: readonly SelectOption[];
  jointIncomeSources: readonly SelectOption[];
  /** How many payments are booked to it, which go too if it is deleted. */
  booked: number;
  /** Save the draft; rejects with a message to show when it can't. */
  onSave: (draft: SubscriptionDraft) => Promise<void>;
  /** Delete the subscription being edited; rejects with a message to show when it can't. */
  onDelete: () => Promise<void>;
  onCancel: () => void;
};

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** A subscription's fields, or a joint contribution's. Delete asks to be confirmed. */
export function SubscriptionForm({
  subscription,
  initial,
  contribution,
  bankAccounts,
  categories,
  jointBankAccounts,
  jointIncomeSources,
  booked,
  onSave,
  onDelete,
  onCancel,
}: SubscriptionFormProps) {
  const [typed, setDraft] = useState(initial);
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  // With only one account there is nothing to choose, even once it loads after the form opens.
  const onlyAccount = bankAccounts.length === 1 ? (bankAccounts[0]?.value ?? null) : null;
  const draft = { ...typed, bankAccountId: typed.bankAccountId ?? onlyAccount };
  const errors = touched ? subscriptionDraftErrors(draft, contribution) : {};

  function change(fields: Partial<SubscriptionDraft>) {
    setDraft((current) => ({ ...current, ...fields }));
  }

  async function run(action: () => Promise<void>) {
    setSaving(true);
    setFailure(null);
    try {
      await action();
    } catch (error) {
      setFailure(messageOf(error));
      setSaving(false);
    }
  }

  function save() {
    setTouched(true);
    if (Object.keys(subscriptionDraftErrors(draft, contribution)).length > 0) return;
    void run(() => onSave(draft));
  }

  if (confirmingDelete && subscription) {
    return (
      <>
        <AppText>Delete “{subscription.name}”?</AppText>
        {booked > 0 ? (
          <AppText tone="muted">
            The {booked === 1 ? 'payment' : `${booked} payments`} it booked go too, including past
            ones, which changes your balances. To stop it and keep them, turn off Active instead.
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
        onChangeText={(name) => change({ name })}
        placeholder={contribution ? 'e.g. Monthly to joint' : 'e.g. Netflix'}
        error={errors.name}
      />
      <TextField
        label="Amount"
        value={draft.amount}
        onChangeText={(amount) => change({ amount })}
        inputMode="decimal"
        placeholder="0.00"
        error={errors.amount}
      />
      <AppText variant="caption" tone="muted">
        What goes out each time it is due. A payment already booked keeps its amount.
      </AppText>
      <SelectField
        label="How often"
        value={draft.cadence}
        options={CADENCES}
        onChange={(cadence) => {
          if (cadence) change({ cadence: cadence as Cadence });
        }}
      />
      <SelectField
        label={contribution ? 'From (personal)' : 'Bank account'}
        value={draft.bankAccountId}
        options={bankAccounts}
        onChange={(bankAccountId) => change({ bankAccountId })}
        error={errors.bankAccountId}
      />
      {contribution ? (
        <>
          <SelectField
            label="To (joint)"
            value={draft.jointBankAccountId}
            options={jointBankAccounts}
            onChange={(jointBankAccountId) => change({ jointBankAccountId })}
            error={errors.jointBankAccountId}
          />
          <SelectField
            label="Joint income source"
            value={draft.jointIncomeSourceId}
            options={jointIncomeSources}
            onChange={(jointIncomeSourceId) => change({ jointIncomeSourceId })}
            error={errors.jointIncomeSourceId}
          />
          <AppText variant="caption" tone="muted">
            Each payment leaves your personal account and arrives in the joint one.
          </AppText>
        </>
      ) : (
        <>
          <SelectField
            label="Category"
            value={draft.categoryId}
            options={categories}
            onChange={(categoryId) => change({ categoryId })}
            noneLabel="None"
          />
          <AppText variant="caption" tone="muted">
            The budget tracker or category this comes out of.
          </AppText>
        </>
      )}
      <DateField
        label="Starts"
        value={draft.startDate}
        onChange={(startDate) => change({ startDate })}
        error={errors.startDate}
      />
      <AppText variant="caption" tone="muted">
        The first date it is due.
      </AppText>
      <DateField
        label="Ends"
        value={draft.endDate}
        onChange={(endDate) => change({ endDate })}
        error={errors.endDate}
        optional
        quickPicks={false}
      />
      <AppText variant="caption" tone="muted">
        The last date it is due. Leave it empty if it is ongoing.
      </AppText>
      <SwitchField
        label="Active"
        caption="Turn off to stop it booking payments. Any still to come are removed."
        value={draft.isActive}
        onChange={(isActive) => change({ isActive })}
      />
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button title={subscription ? 'Save' : 'Add'} onPress={save} disabled={saving} />
      {subscription ? (
        <Button title="Delete" variant="destructive" onPress={() => setConfirmingDelete(true)} />
      ) : null}
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}
