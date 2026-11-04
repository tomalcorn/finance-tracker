import { useState } from 'react';

import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { DateField } from '@/components/DateField';
import { SelectField, type SelectOption } from '@/components/SelectField';
import { TextField } from '@/components/TextField';
import {
  contributionDraftErrors,
  contributionDraftOf,
  contributionOf,
} from '@/contributions/contributionDraft';
import { today } from '@/domain/entities';
import type { Contribution } from '@/ports/repositories';

type ContributeFormProps = {
  /** The personal accounts the money can leave. */
  personalAccounts: readonly SelectOption[];
  /** The joint accounts it can arrive in. */
  jointAccounts: readonly SelectOption[];
  /** The joint income sources it can be booked against. */
  incomeSources: readonly SelectOption[];
  /** Make the contribution; rejects with a message to show when it can't. */
  onContribute: (contribution: Contribution) => Promise<void>;
  onCancel: () => void;
};

/**
 * Move money from a personal account into the joint one. Says what is missing instead when there
 * is no joint account or joint income source to use.
 */
export function ContributeForm({
  personalAccounts,
  jointAccounts,
  incomeSources,
  onContribute,
  onCancel,
}: ContributeFormProps) {
  const [draft, setDraft] = useState(() =>
    contributionDraftOf(today(), personalAccounts, jointAccounts, incomeSources),
  );
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const errors = touched ? contributionDraftErrors(draft) : {};

  if (jointAccounts.length === 0) {
    return (
      <>
        <AppText>You need a joint bank account to contribute to.</AppText>
        <AppText tone="muted">
          Add one under Bank accounts on the Joint tab, then come back to make a contribution.
        </AppText>
        <Button title="Close" variant="plain" onPress={onCancel} />
      </>
    );
  }

  if (incomeSources.length === 0) {
    return (
      <>
        <AppText>You need a joint income source to contribute against.</AppText>
        <AppText tone="muted">
          It’s how the money shows up in the joint budget. Add one under Income split on the Joint
          tab, then come back to make a contribution.
        </AppText>
        <Button title="Close" variant="plain" onPress={onCancel} />
      </>
    );
  }

  async function contribute() {
    setTouched(true);
    const contribution = contributionOf(draft);
    if (!contribution) return;
    setSaving(true);
    setFailure(null);
    try {
      await onContribute(contribution);
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

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
        label="From (personal)"
        value={draft.fromBankAccountId}
        options={personalAccounts}
        onChange={(fromBankAccountId) => setDraft((current) => ({ ...current, fromBankAccountId }))}
        error={errors.fromBankAccountId}
      />
      <SelectField
        label="To (joint)"
        value={draft.toBankAccountId}
        options={jointAccounts}
        onChange={(toBankAccountId) => setDraft((current) => ({ ...current, toBankAccountId }))}
        error={errors.toBankAccountId}
      />
      <SelectField
        label="Income source (joint)"
        value={draft.incomeSourceId}
        options={incomeSources}
        onChange={(incomeSourceId) => setDraft((current) => ({ ...current, incomeSourceId }))}
        error={errors.incomeSourceId}
      />
      <DateField
        label="Date"
        value={draft.date}
        onChange={(date) => setDraft((current) => ({ ...current, date }))}
        error={errors.date}
      />
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button title="Contribute" onPress={() => void contribute()} disabled={saving} />
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}
