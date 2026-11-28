import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { SegmentedControl } from '@/components/SegmentedControl';
import { Sheet, useSheet } from '@/components/Sheet';
import { useToast } from '@/components/Toast';
import type { OwnershipType } from '@/domain/entities';
import type { QuickButtonView } from '@/domain/readModels';
import { useRepositories, useRows } from '@/hooks/repositories';
import { messageOf } from '@/hooks/submit';
import { categoryOptions, nameOptions } from '@/lookups';
import { ButtonForm } from '@/quickExpenses/ButtonForm';
import { draftRow, nextPosition, ordered, type ButtonDraft } from '@/quickExpenses/buttonDraft';
import { LogPaymentForm } from '@/quickExpenses/LogPaymentForm';
import { NewButtonTile, QuickButtonTile } from '@/quickExpenses/QuickButtonTile';
import { formatAmount } from '@/theme/formatAmount';
import { SPACING } from '@/theme/tokens';
import { logQuickPayment, type PaymentOverrides } from '@/useCases/logQuickPayment';

/** What the sheet is showing: a payment to finish, or a button's settings. */
type SheetTarget =
  { kind: 'log'; button: QuickButtonView } | { kind: 'edit'; button: QuickButtonView | null };

const OWNERSHIPS: readonly { value: OwnershipType; label: string }[] = [
  { value: 'personal', label: 'Personal' },
  { value: 'joint', label: 'Joint' },
];

const COLUMNS = 2;

/** Split the tiles into rows of `COLUMNS`. */
function rowsOf<T>(items: readonly T[]): T[][] {
  const rows: T[][] = [];
  for (let start = 0; start < items.length; start += COLUMNS) {
    rows.push(items.slice(start, start + COLUMNS));
  }
  return rows;
}

/** Log a preset expense in one tap, and manage the buttons that do it. */
export default function QuickExpensesScreen() {
  const repositories = useRepositories();
  const jointAccounts = useRows(repositories.jointAccounts());
  const hasJointAccount = (jointAccounts.data?.length ?? 0) > 0;
  const [chosenOwnership, setOwnership] = useState<OwnershipType>('personal');
  const ownership = hasJointAccount ? chosenOwnership : 'personal';

  const quickButtons = repositories.quickButtons(ownership);
  const payments = repositories.payments(ownership);
  const buttons = useRows(quickButtons);
  const bankAccounts = useRows(repositories.bankAccounts(ownership));
  const categories = useRows(repositories.categories(ownership));
  const bankAccountOptions = nameOptions(bankAccounts.data ?? []);
  const categoryChoices = categoryOptions(categories.data ?? []);
  const shown = ordered(buttons.data ?? []);

  const [editing, setEditing] = useState(false);
  const sheet = useSheet<SheetTarget>();
  const [busyId, setBusyId] = useState<string | null>(null);
  const { notify } = useToast();

  async function log(button: QuickButtonView, overrides?: PaymentOverrides) {
    const payment = await logQuickPayment(payments, button, overrides);
    notify(`${payment.name} — ${formatAmount(payment.expense)} logged`, {
      label: 'Undo',
      onPress: () => {
        payments.delete([payment.id]).then(
          () => notify('Payment removed'),
          (error: unknown) => notify(`Could not undo: ${messageOf(error)}`),
        );
      },
    });
  }

  async function tap(button: QuickButtonView) {
    if (editing) {
      sheet.open({ kind: 'edit', button });
      return;
    }
    if (button.mode === 'prompt') {
      sheet.open({ kind: 'log', button });
      return;
    }
    setBusyId(button.id);
    try {
      await log(button);
    } catch (error) {
      notify(messageOf(error));
    } finally {
      setBusyId(null);
    }
  }

  async function saveButton(draft: ButtonDraft, button: QuickButtonView | null) {
    await quickButtons.save(await quickButtons.build([draftRow(draft, button)]));
    sheet.close();
    notify(button ? `${draft.name.trim()} saved` : `${draft.name.trim()} added`);
  }

  async function removeButton(button: QuickButtonView) {
    await quickButtons.delete([button.id]);
    sheet.close();
    notify(`${button.name} removed`);
  }

  const { target } = sheet;
  const sheetTitle =
    target?.kind === 'log'
      ? `Log ${target.button.name}`
      : target?.button
        ? `Edit ${target.button.name}`
        : 'New quick button';

  return (
    <>
      <Screen
        title="Quick Expenses"
        action={
          shown.length > 0 ? (
            <Button
              title={editing ? 'Done' : 'Edit'}
              variant={editing ? 'secondary' : 'plain'}
              onPress={() => setEditing(!editing)}
            />
          ) : null
        }
      >
        {hasJointAccount ? (
          <SegmentedControl
            label="Log against"
            value={ownership}
            options={OWNERSHIPS}
            onChange={setOwnership}
          />
        ) : null}
        <AppText tone="muted">
          {editing
            ? 'Tap a button to change or remove it.'
            : 'Tap to log an expense. Hold to edit the button.'}
        </AppText>

        {buttons.error ? (
          <AppText tone="negative">
            Could not load your quick buttons: {buttons.error.message}
          </AppText>
        ) : buttons.isPending ? (
          <AppText tone="muted">Loading…</AppText>
        ) : shown.length === 0 ? (
          <View style={styles.empty}>
            <AppText variant="heading">No quick buttons yet</AppText>
            <AppText tone="muted">
              Add one for something you buy often, like a coffee or a bus fare, and log it from here
              with one tap.
            </AppText>
            <Button
              title="Add a quick button"
              onPress={() => sheet.open({ kind: 'edit', button: null })}
            />
          </View>
        ) : (
          <View style={styles.grid}>
            {rowsOf<QuickButtonView | null>(editing ? [...shown, null] : shown).map((row) => (
              <View key={row.map((button) => button?.id ?? 'new').join()} style={styles.row}>
                {row.map((button) =>
                  button ? (
                    <QuickButtonTile
                      key={button.id}
                      button={button}
                      editing={editing}
                      busy={busyId === button.id}
                      onPress={() => void tap(button)}
                      onLongPress={() => sheet.open({ kind: 'edit', button })}
                    />
                  ) : (
                    <NewButtonTile
                      key="new"
                      onPress={() => sheet.open({ kind: 'edit', button: null })}
                    />
                  ),
                )}
                {row.length < COLUMNS ? <View style={styles.spacer} /> : null}
              </View>
            ))}
          </View>
        )}
      </Screen>

      <Sheet visible={sheet.visible} onClose={sheet.close} title={sheetTitle}>
        {target?.kind === 'log' ? (
          <LogPaymentForm
            key={sheet.key}
            button={target.button}
            bankAccounts={bankAccountOptions}
            categories={categoryChoices}
            onSubmit={async (overrides) => {
              await log(target.button, overrides);
              sheet.close();
            }}
            onCancel={sheet.close}
          />
        ) : target ? (
          <ButtonForm
            key={sheet.key}
            button={target.button}
            position={nextPosition(shown)}
            bankAccounts={bankAccountOptions}
            categories={categoryChoices}
            onSave={(draft) => saveButton(draft, target.button)}
            onRemove={() => (target.button ? removeButton(target.button) : Promise.resolve())}
            onCancel={sheet.close}
          />
        ) : null}
      </Sheet>
    </>
  );
}

const styles = StyleSheet.create({
  grid: { gap: SPACING.md },
  row: { flexDirection: 'row', gap: SPACING.md },
  spacer: { flex: 1 },
  empty: { gap: SPACING.md, paddingVertical: SPACING.xl },
});
