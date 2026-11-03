import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { balanceTrend } from '@/bankAccounts/balanceTrend';
import { BankAccountForm } from '@/bankAccounts/BankAccountForm';
import { bankAccountRow, type BankAccountDraft } from '@/bankAccounts/bankAccountDraft';
import { byName, isInUse, totalBalance } from '@/bankAccounts/bankAccountList';
import { BankAccountTile, BankAccountTileSpacer } from '@/bankAccounts/BankAccountTile';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card, CardHeading } from '@/components/Card';
import { Sheet } from '@/components/Sheet';
import { today, type OwnershipType } from '@/domain/entities';
import type { BankAccountView } from '@/domain/readModels';
import { useRepositories, useRows } from '@/hooks/repositories';
import { formatAmount } from '@/theme/formatAmount';
import { SPACING } from '@/theme/tokens';

type BankAccountsSectionProps = {
  ownership: OwnershipType;
  /** Reports an account added or deleted, once its sheet has closed. */
  onNotify: (text: string) => void;
};

/** A tile per account and their total, with each tile opening to edit or delete the account. */
export function BankAccountsSection({ ownership, onNotify }: BankAccountsSectionProps) {
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

  const rows = byName(accounts.data ?? []);
  const editing = sheet?.account ?? null;
  const now = today();

  function open(account: BankAccountView | null) {
    setSheet((current) => ({ account, key: (current?.key ?? 0) + 1 }));
    setSheetOpen(true);
  }

  async function save(draft: BankAccountDraft) {
    const row = bankAccountRow(draft, editing);
    await accountsRepository.save(await accountsRepository.build([row]));
    closeSheet();
    if (!editing) onNotify(`${draft.name.trim()} added`);
  }

  async function remove() {
    if (!editing) return;
    await accountsRepository.delete([editing.id]);
    closeSheet();
    onNotify(`${editing.name} deleted`);
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
    <View style={styles.section}>
      {accounts.error ? (
        <AppText tone="negative">Could not load your accounts: {accounts.error.message}</AppText>
      ) : accounts.isPending ? (
        <AppText tone="muted">Loading…</AppText>
      ) : rows.length === 0 ? (
        <Card title="Bank accounts">
          <AppText tone="muted">No bank accounts yet. Add one to track its balance.</AppText>
        </Card>
      ) : (
        <>
          <CardHeading title="Bank accounts" detail={`${formatAmount(totalBalance(rows))} total`} />
          <View style={styles.tiles}>
            {rows.map((account) => (
              <BankAccountTile
                key={account.id}
                name={account.name}
                balance={account.current_balance}
                trend={payments.data ? balanceTrend(account, payments.data, now) : null}
                onPress={() => open(account)}
              />
            ))}
            {rows.length % 2 === 1 ? <BankAccountTileSpacer /> : null}
          </View>
          {payments.error ? (
            <AppText tone="negative">Could not load the trends: {payments.error.message}</AppText>
          ) : null}
        </>
      )}

      <Button title="Add a bank account" variant="secondary" onPress={() => open(null)} />

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
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: SPACING.sm },
  tiles: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.md },
});
