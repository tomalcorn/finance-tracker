import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { BankAccountForm } from '@/bankAccounts/BankAccountForm';
import { bankAccountRow, type BankAccountDraft } from '@/bankAccounts/bankAccountDraft';
import { byName, isInUse, totalBalance } from '@/bankAccounts/bankAccountList';
import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ListRow } from '@/components/ListRow';
import { Screen } from '@/components/Screen';
import { Sheet } from '@/components/Sheet';
import { Toast, type ToastMessage } from '@/components/Toast';
import type { OwnershipType } from '@/domain/entities';
import type { BankAccountView } from '@/domain/readModels';
import { useRepositories, useRows } from '@/hooks/repositories';
import { formatAmount } from '@/theme/formatAmount';

type BankAccountsScreenProps = { ownership: OwnershipType };

/** Each account's current balance and their total, with a row opening to edit or delete it. */
export function BankAccountsScreen({ ownership }: BankAccountsScreenProps) {
  const repositories = useRepositories();
  const accountsRepository = repositories.bankAccounts(ownership);
  const accounts = useRows(accountsRepository);
  const payments = useRows(repositories.payments(ownership));
  const subscriptions = useRows(repositories.subscriptions(ownership));
  // A personal contribution's income leg can arrive in a joint account.
  const personalSubscriptions = useRows(repositories.subscriptions('personal'));
  const quickButtons = useRows(repositories.quickButtons(ownership));
  const [sheet, setSheet] = useState<{ account: BankAccountView | null; key: number } | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const closeSheet = useCallback(() => setSheetOpen(false), []);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const dismissToast = useCallback(() => setToast(null), []);

  const rows = byName(accounts.data ?? []);
  const editing = sheet?.account ?? null;

  function notify(text: string) {
    setToast((current) => ({ id: (current?.id ?? 0) + 1, text }));
  }

  function open(account: BankAccountView | null) {
    setSheet((current) => ({ account, key: (current?.key ?? 0) + 1 }));
    setSheetOpen(true);
  }

  async function save(draft: BankAccountDraft) {
    const row = bankAccountRow(draft, editing);
    await accountsRepository.save(await accountsRepository.build([row]));
    closeSheet();
    if (!editing) notify(`${draft.name.trim()} added`);
  }

  async function remove() {
    if (!editing) return;
    await accountsRepository.delete([editing.id]);
    closeSheet();
    notify(`${editing.name} deleted`);
  }

  /** Known only once everything that could use the account has loaded. */
  function deletable(account: BankAccountView): boolean {
    if (!payments.data || !subscriptions.data || !personalSubscriptions.data) return false;
    return !isInUse(account.id, payments.data, [
      ...subscriptions.data,
      ...personalSubscriptions.data,
    ]);
  }

  return (
    <View style={styles.fill}>
      <Screen title="Bank accounts" back>
        {accounts.error ? (
          <AppText tone="negative">Could not load your accounts: {accounts.error.message}</AppText>
        ) : accounts.isPending ? (
          <AppText tone="muted">Loading…</AppText>
        ) : rows.length === 0 ? (
          <Card>
            <AppText tone="muted">No bank accounts yet. Add one to track its balance.</AppText>
          </Card>
        ) : (
          <>
            <Card>
              <AppText variant="heading">{formatAmount(totalBalance(rows))}</AppText>
              <AppText tone="muted">
                Across {rows.length} {rows.length === 1 ? 'account' : 'accounts'}
              </AppText>
            </Card>
            <Card list>
              {rows.map((account) => (
                <ListRow
                  key={account.id}
                  title={account.name}
                  subtitle={`Started at ${formatAmount(account.starting_balance)}`}
                  trailing={<Amount value={account.current_balance} />}
                  onPress={() => open(account)}
                />
              ))}
            </Card>
          </>
        )}

        <Button title="Add a bank account" variant="secondary" onPress={() => open(null)} />
      </Screen>

      <Sheet
        visible={sheetOpen}
        onClose={closeSheet}
        title={editing ? `Edit ${editing.name}` : 'New bank account'}
      >
        {sheet ? (
          <BankAccountForm
            key={sheet.key}
            account={editing}
            deletable={editing ? deletable(editing) : false}
            quickButtons={
              (quickButtons.data ?? []).filter((button) => button.bank_account_id === editing?.id)
                .length
            }
            onSave={save}
            onDelete={remove}
            onCancel={closeSheet}
          />
        ) : null}
      </Sheet>
      <Toast toast={toast} onDismiss={dismissToast} />
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
});
