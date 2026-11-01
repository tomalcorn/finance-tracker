import { useState } from 'react';

import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { TextField } from '@/components/TextField';
import type { CategoryView } from '@/domain/readModels';
import { categoryDraftErrors, categoryDraftOf, type CategoryDraft } from '@/budget/categoryDraft';

type CategoryFormProps = {
  /** The subcategory being edited, or null to add one. */
  category: CategoryView | null;
  /** The tracker it sits under. */
  root: CategoryView;
  /** It is a pot, filled up across months, rather than a monthly budget. */
  pot: boolean;
  /** Save the draft; rejects with a message to show when it can't. */
  onSave: (draft: CategoryDraft) => Promise<void>;
  /** Delete the subcategory being edited; rejects with a message to show when it can't. */
  onDelete: () => Promise<void>;
  onCancel: () => void;
};

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * A subcategory's settings. A new one takes its name and amounts: a monthly budget, or a pot's
 * target and plan. An existing one is renamed or deleted here, its amounts edited on its screen.
 */
export function CategoryForm({
  category,
  root,
  pot,
  onSave,
  onDelete,
  onCancel,
}: CategoryFormProps) {
  const [draft, setDraft] = useState(() => categoryDraftOf(category));
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const errors = categoryDraftErrors(draft, pot);
  const shown = touched ? errors : {};

  function update(changes: Partial<CategoryDraft>) {
    setDraft((current) => ({ ...current, ...changes }));
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
    if (Object.keys(errors).length > 0) return;
    void run(() => onSave(draft));
  }

  if (confirmingDelete && category) {
    return (
      <>
        <AppText>
          Delete “{category.name}”? Payments booked to it move to {root.name}.
        </AppText>
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
        onChangeText={(name) => update({ name })}
        placeholder={pot ? 'e.g. New bike' : 'e.g. Groceries'}
        error={shown.name}
      />
      {category ? null : pot ? (
        <>
          <TextField
            label="Cost"
            value={draft.cost}
            onChangeText={(cost) => update({ cost })}
            inputMode="decimal"
            placeholder="0.00"
            error={shown.cost}
          />
          <TextField
            label="Planned this month"
            value={draft.budget}
            onChangeText={(budget) => update({ budget })}
            inputMode="decimal"
            placeholder="0.00"
            error={shown.budget}
          />
          <AppText variant="caption" tone="muted">
            What you mean to put towards it this month.
          </AppText>
          <TextField
            label="Already saved"
            value={draft.startingBalance}
            onChangeText={(startingBalance) => update({ startingBalance })}
            inputMode="decimal"
            placeholder="0.00"
            error={shown.startingBalance}
          />
        </>
      ) : (
        <TextField
          label="Monthly budget"
          value={draft.budget}
          onChangeText={(budget) => update({ budget })}
          inputMode="decimal"
          placeholder="0.00"
          error={shown.budget}
        />
      )}
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button title="Save" onPress={save} disabled={saving} />
      {category ? (
        <Button title="Delete" variant="destructive" onPress={() => setConfirmingDelete(true)} />
      ) : null}
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}

type BudgetFormProps = {
  tracker: CategoryView;
  /** Save the budget as typed; rejects with a message to show when it can't. */
  onSave: (budget: string) => Promise<void>;
  validate: (budget: string) => string | undefined;
  onCancel: () => void;
};

/** A tracker's monthly budget: its share of the income. */
export function BudgetForm({ tracker, onSave, validate, onCancel }: BudgetFormProps) {
  const [budget, setBudget] = useState(tracker.budget.toFixed(2));
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const error = validate(budget);

  async function save() {
    setTouched(true);
    if (error) return;
    setSaving(true);
    setFailure(null);
    try {
      await onSave(budget);
    } catch (failed) {
      setFailure(messageOf(failed));
      setSaving(false);
    }
  }

  return (
    <>
      <TextField
        label="Monthly budget"
        value={budget}
        onChangeText={setBudget}
        inputMode="decimal"
        placeholder="0.00"
        error={touched ? error : undefined}
      />
      <AppText variant="caption" tone="muted">
        How much of each month’s income goes to {tracker.name}.
      </AppText>
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button title="Save" onPress={() => void save()} disabled={saving} />
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}
