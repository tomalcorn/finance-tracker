import { useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { dailyBalances, sampled } from '@/bankAccounts/balanceTrend';
import { BankAccountForm } from '@/bankAccounts/BankAccountForm';
import { bankAccountRow, type BankAccountDraft } from '@/bankAccounts/bankAccountDraft';
import { byName, totalBalance } from '@/bankAccounts/bankAccountList';
import { BankAccountTile, BankAccountTileSpacer } from '@/bankAccounts/BankAccountTile';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card, CardHeading } from '@/components/Card';
import { Sheet } from '@/components/Sheet';
import { today, type OwnershipType } from '@/domain/entities';
import { useRepositories, useRows } from '@/hooks/repositories';
import { formatAmount } from '@/theme/formatAmount';
import { SPACING } from '@/theme/tokens';

type BankAccountsSectionProps = {
  ownership: OwnershipType;
  /** Reports an account added, once its sheet has closed. */
  onNotify: (text: string) => void;
};

/** A tile per account and their total, with each tile opening the account's own page. */
export function BankAccountsSection({ ownership, onNotify }: BankAccountsSectionProps) {
  const router = useRouter();
  const repositories = useRepositories();
  const accountsRepository = repositories.bankAccounts(ownership);
  const accounts = useRows(accountsRepository);
  const payments = useRows(repositories.payments(ownership));
  const [addKey, setAddKey] = useState<number | null>(null);
  const [adding, setAdding] = useState(false);
  const closeAdd = useCallback(() => setAdding(false), []);

  const rows = byName(accounts.data ?? []);
  const now = today();

  function startAdding() {
    setAddKey((current) => (current ?? 0) + 1);
    setAdding(true);
  }

  function open(id: string) {
    router.push(
      ownership === 'personal'
        ? { pathname: '/personal/account/[id]', params: { id } }
        : { pathname: '/joint/account/[id]', params: { id } },
    );
  }

  async function add(draft: BankAccountDraft) {
    const row = bankAccountRow(draft, null);
    await accountsRepository.save(await accountsRepository.build([row]));
    closeAdd();
    onNotify(`${draft.name.trim()} added`);
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
                trend={
                  payments.data
                    ? sampled(dailyBalances(account, payments.data, now)).map(
                        (point) => point.balance,
                      )
                    : null
                }
                onPress={() => open(account.id)}
              />
            ))}
            {rows.length % 2 === 1 ? <BankAccountTileSpacer /> : null}
          </View>
          {payments.error ? (
            <AppText tone="negative">Could not load the trends: {payments.error.message}</AppText>
          ) : null}
        </>
      )}

      <Button title="Add a bank account" variant="secondary" onPress={startAdding} />

      <Sheet visible={adding} onClose={closeAdd} title="New bank account">
        {addKey !== null ? (
          <BankAccountForm key={addKey} account={null} onSave={add} onCancel={closeAdd} />
        ) : null}
      </Sheet>
    </View>
  );
}

const styles = StyleSheet.create({
  section: { gap: SPACING.sm },
  tiles: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.md },
});
