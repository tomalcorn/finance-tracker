import { useState } from 'react';
import { StyleSheet, Switch, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { DateField } from '@/components/DateField';
import { SegmentedControl } from '@/components/SegmentedControl';
import { SelectField, type SelectOption } from '@/components/SelectField';
import { TextField } from '@/components/TextField';
import type { PaymentView } from '@/domain/readModels';
import { paymentDraftErrors, type PaymentDraft, type PaymentType } from '@/payments/paymentDraft';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

const TYPES: readonly { value: PaymentType; label: string }[] = [
  { value: 'expense', label: 'Money out' },
  { value: 'income', label: 'Money in' },
];

type PaymentFormProps = {
  /** The payment being edited, or null to add one. */
  payment: PaymentView | null;
  initial: PaymentDraft;
  /** The accounts to choose from; the only one is chosen for you. */
  bankAccounts: readonly SelectOption[];
  categories: readonly SelectOption[];
  incomeSources: readonly SelectOption[];
  /** Save the draft; rejects with a message to show when it can't. */
  onSave: (draft: PaymentDraft) => Promise<void>;
  /** Delete the payment being edited; rejects with a message to show when it can't. */
  onDelete: () => Promise<void>;
  onCancel: () => void;
};

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * A payment's fields. Adding one chooses money out or in first; an existing payment keeps its kind.
 * Delete asks to be confirmed.
 */
export function PaymentForm({
  payment,
  initial,
  bankAccounts,
  categories,
  incomeSources,
  onSave,
  onDelete,
  onCancel,
}: PaymentFormProps) {
  const { colors } = useAppTheme();
  const [typed, setDraft] = useState(initial);
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  // With only one account there is nothing to choose, even once it loads after the form opens.
  const onlyAccount = bankAccounts.length === 1 ? (bankAccounts[0]?.value ?? null) : null;
  const draft = { ...typed, bankAccountId: typed.bankAccountId ?? onlyAccount };
  const errors = touched ? paymentDraftErrors(draft) : {};
  const income = draft.type === 'income';

  function change(fields: Partial<PaymentDraft>) {
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
    if (Object.keys(paymentDraftErrors(draft)).length > 0) return;
    void run(() => onSave(draft));
  }

  if (confirmingDelete && payment) {
    return (
      <>
        <AppText>Delete “{payment.name}”?</AppText>
        {payment.linked_payment_id ? (
          <AppText tone="muted">
            The other half of the joint contribution stays where it is.
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
      {payment ? null : (
        <SegmentedControl
          label="Kind of payment"
          value={draft.type}
          options={TYPES}
          // A category is not an income source, so the choice made for the other kind goes.
          onChange={(type) => change({ type, sourceId: null })}
        />
      )}
      {payment?.subscription_id ? (
        <AppText variant="caption" tone="muted">
          Booked by a subscription.
        </AppText>
      ) : null}
      {payment?.linked_payment_id ? (
        <AppText variant="caption" tone="muted">
          One half of a joint contribution.
        </AppText>
      ) : null}
      <TextField
        label="Name"
        value={draft.name}
        onChangeText={(name) => change({ name })}
        placeholder={income ? 'e.g. Salary' : 'e.g. Groceries'}
        error={errors.name}
      />
      <TextField
        label={income ? 'Amount in' : 'Amount out'}
        value={draft.amount}
        onChangeText={(amount) => change({ amount })}
        inputMode="decimal"
        placeholder="0.00"
        error={errors.amount}
      />
      <DateField
        label="Date"
        value={draft.date}
        onChange={(date) => change({ date })}
        error={errors.date}
      />
      <SelectField
        label="Bank account"
        value={draft.bankAccountId}
        options={bankAccounts}
        onChange={(bankAccountId) => change({ bankAccountId })}
        error={errors.bankAccountId}
      />
      <AppText variant="caption" tone="muted">
        Which account the money moved through.
      </AppText>
      {income ? (
        <SelectField
          label="Income source"
          value={draft.sourceId}
          options={incomeSources}
          onChange={(sourceId) => change({ sourceId })}
          noneLabel="None"
        />
      ) : (
        <SelectField
          label="Category"
          value={draft.sourceId}
          options={categories}
          onChange={(sourceId) => change({ sourceId })}
          noneLabel="None"
        />
      )}
      <AppText variant="caption" tone="muted">
        {income
          ? 'Which income source this income goes against.'
          : 'The budget tracker or category this comes out of.'}
      </AppText>
      <View style={styles.toggle}>
        <View style={styles.toggleText}>
          <AppText variant="label">Checked</AppText>
          <AppText variant="caption" tone="muted">
            Tick once you’ve matched it against your real bank balance.
          </AppText>
        </View>
        <Switch
          aria-label="Checked"
          value={draft.checked}
          onValueChange={(checked) => change({ checked })}
          trackColor={{ true: colors.accent, false: colors.surfaceMuted }}
        />
      </View>
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
      <Button title={payment ? 'Save' : 'Add payment'} onPress={save} disabled={saving} />
      {payment ? (
        <Button title="Delete" variant="destructive" onPress={() => setConfirmingDelete(true)} />
      ) : null}
      <Button title="Cancel" variant="plain" onPress={onCancel} />
    </>
  );
}

const styles = StyleSheet.create({
  toggle: { flexDirection: 'row', alignItems: 'center', gap: SPACING.md },
  toggleText: { flex: 1, gap: 2 },
});
