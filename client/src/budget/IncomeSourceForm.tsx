import { useState } from 'react';

import { incomeSourceDraftOf, type IncomeSourceDraft } from '@/budget/incomeSources';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { CheckList } from '@/components/CheckList';
import { TextField } from '@/components/TextField';
import type { CategoryView, IncomeSourceView } from '@/domain/readModels';

type IncomeSourceFormProps = {
  /** The source being edited, or null to add one. */
  source: IncomeSourceView | null;
  /** The budget trackers it can fund. */
  trackers: readonly CategoryView[];
  /** Whether it can be deleted: the database refuses while payments are booked to it. */
  deletable: boolean;
  /** Save the draft; rejects with a message to show when it can't. */
  onSave: (draft: IncomeSourceDraft) => Promise<void>;
  /** Delete the source being edited; rejects with a message to show when it can't. */
  onDelete: () => Promise<void>;
  onCancel: () => void;
};

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** An income source's settings: its name, and which budget trackers it funds. */
export function IncomeSourceForm({
  source,
  trackers,
  deletable,
  onSave,
  onDelete,
  onCancel,
}: IncomeSourceFormProps) {
  const [draft, setDraft] = useState(() => incomeSourceDraftOf(source));
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const nameError = draft.name.trim() ? undefined : 'Give it a name.';

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
    if (nameError) return;
    void run(() => onSave(draft));
  }

  if (confirmingDelete && source) {
    return (
      <>
        <AppText>Delete “{source.name}”?</AppText>
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
        placeholder="e.g. Salary"
        error={touched ? nameError : undefined}
      />
      <CheckList
        label="Funds"
        options={trackers.map((tracker) => ({ value: tracker.id, label: tracker.name }))}
        selected={draft.trackerIds}
        onChange={(trackerIds) => setDraft((current) => ({ ...current, trackerIds }))}
      />
      <AppText variant="caption" tone="muted">
        The budget trackers this income is split between.
      </AppText>
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button title="Save" onPress={save} disabled={saving} />
      {source && deletable ? (
        <Button title="Delete" variant="destructive" onPress={() => setConfirmingDelete(true)} />
      ) : null}
      {source && !deletable ? (
        <AppText variant="caption" tone="muted">
          It can’t be deleted while payments are booked to it.
        </AppText>
      ) : null}
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}
