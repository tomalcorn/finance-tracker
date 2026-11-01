import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { SegmentedControl } from '@/components/SegmentedControl';
import { SelectField, type SelectOption } from '@/components/SelectField';
import { TextField } from '@/components/TextField';
import type { QuickButtonMode } from '@/domain/entities';
import type { QuickButtonView } from '@/domain/readModels';
import { draftErrors, draftOf, type ButtonDraft } from '@/quickExpenses/buttonDraft';
import { SPACING } from '@/theme/tokens';

type ButtonFormProps = {
  /** The button being edited, or null to add one. */
  button: QuickButtonView | null;
  /** Where a new button goes. */
  position: number;
  bankAccounts: readonly SelectOption[];
  categories: readonly SelectOption[];
  /** Save the button; rejects with a message to show when it can't. */
  onSave: (draft: ButtonDraft) => Promise<void>;
  /** Remove the button being edited; rejects with a message to show when it can't. */
  onRemove: () => Promise<void>;
  onCancel: () => void;
};

const MODES: readonly { value: QuickButtonMode; label: string }[] = [
  { value: 'log', label: 'Log at once' },
  { value: 'prompt', label: 'Ask first' },
];

/** A quick button's settings: what it is called, and the payment it presets. */
export function ButtonForm({
  button,
  position,
  bankAccounts,
  categories,
  onSave,
  onRemove,
  onCancel,
}: ButtonFormProps) {
  const [draft, setDraft] = useState(() => draftOf(button, position));
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmingRemove, setConfirmingRemove] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const errors = draftErrors(draft);
  const shown = touched ? errors : {};
  const asks = draft.mode === 'prompt';
  const optional = asks ? ' (optional)' : '';

  function update(changes: Partial<ButtonDraft>) {
    setDraft((current) => ({ ...current, ...changes }));
  }

  async function run(action: () => Promise<void>) {
    setSaving(true);
    setFailure(null);
    try {
      await action();
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error));
      setSaving(false);
    }
  }

  function save() {
    setTouched(true);
    if (Object.keys(errors).length > 0) return;
    void run(() => onSave(draft));
  }

  if (confirmingRemove && button) {
    return (
      <>
        <AppText>Remove “{button.name}”? Payments it has logged stay where they are.</AppText>
        {failure ? <AppText tone="negative">{failure}</AppText> : null}
        <Button
          title="Remove button"
          variant="destructive"
          onPress={() => void run(onRemove)}
          disabled={saving}
        />
        <Button title="Keep it" variant="plain" onPress={() => setConfirmingRemove(false)} />
      </>
    );
  }

  return (
    <>
      <View style={styles.row}>
        <View style={styles.name}>
          <TextField
            label="Button name"
            value={draft.name}
            onChangeText={(name) => update({ name })}
            placeholder="e.g. Coffee"
            error={shown.name}
          />
        </View>
        <View style={styles.icon}>
          <TextField
            label="Icon"
            value={draft.icon}
            onChangeText={(icon) => update({ icon })}
            placeholder="Emoji"
            maxLength={4}
          />
        </View>
      </View>
      <View style={styles.mode}>
        <SegmentedControl
          label="When tapped"
          value={draft.mode}
          options={MODES}
          onChange={(mode) => update({ mode })}
        />
        <AppText variant="caption" tone="muted">
          {asks
            ? 'A tap opens a form with these details filled in, to finish before logging.'
            : 'A tap logs the payment straight away, dated today.'}
        </AppText>
      </View>
      <TextField
        label="Payment name (optional)"
        value={draft.paymentName}
        onChangeText={(paymentName) => update({ paymentName })}
        placeholder={asks ? 'Typed in when tapped' : draft.name || 'The button name'}
      />
      <TextField
        label={`Amount${optional}`}
        value={draft.amount}
        onChangeText={(amount) => update({ amount })}
        inputMode="decimal"
        placeholder="0.00"
        error={shown.amount}
      />
      <SelectField
        label={`Bank account${optional}`}
        value={draft.bankAccountId}
        options={bankAccounts}
        onChange={(bankAccountId) => update({ bankAccountId })}
        noneLabel={asks ? 'None' : undefined}
        error={shown.bankAccountId}
      />
      <SelectField
        label="Category (optional)"
        value={draft.categoryId}
        options={categories}
        onChange={(categoryId) => update({ categoryId })}
        noneLabel="None"
      />
      <TextField
        label="Position"
        value={draft.position}
        onChangeText={(text) => update({ position: text })}
        inputMode="numeric"
        error={shown.position}
      />
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button title="Save" onPress={save} disabled={saving} />
      {button ? (
        <Button
          title="Remove button"
          variant="destructive"
          onPress={() => setConfirmingRemove(true)}
        />
      ) : null}
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: SPACING.md },
  name: { flex: 1 },
  icon: { width: 72 },
  mode: { gap: SPACING.xs },
});
