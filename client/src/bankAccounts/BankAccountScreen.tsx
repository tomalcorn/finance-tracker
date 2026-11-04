import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { BalanceChart } from '@/bankAccounts/BalanceChart';
import { dailyBalances, TREND_MONTHS } from '@/bankAccounts/balanceTrend';
import { BankAccountForm } from '@/bankAccounts/BankAccountForm';
import { bankAccountRow, type BankAccountDraft } from '@/bankAccounts/bankAccountDraft';
import { isInUse } from '@/bankAccounts/bankAccountList';
import { AppText } from '@/components/AppText';
import { Card } from '@/components/Card';
import { Screen } from '@/components/Screen';
import { Toast, type ToastMessage } from '@/components/Toast';
import { today, type OwnershipType } from '@/domain/entities';
import { useRepositories, useRows } from '@/hooks/repositories';
import { formatAmount } from '@/theme/formatAmount';

type BankAccountScreenProps = { ownership: OwnershipType };

/** One bank account: its balance charted over the last few months, and its fields to edit. */
export function BankAccountScreen({ ownership }: BankAccountScreenProps) {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const repositories = useRepositories();
  const accountsRepository = repositories.bankAccounts(ownership);
  const accounts = useRows(accountsRepository);
  const payments = useRows(repositories.payments(ownership));
  const subscriptions = useRows(repositories.subscriptions(ownership));
  // A personal contribution's income leg can arrive in a joint account.
  const personalSubscriptions = useRows(repositories.subscriptions('personal'));
  const quickButtons = useRows(repositories.quickButtons(ownership));
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const dismissToast = useCallback(() => setToast(null), []);

  const account = accounts.data?.find((row) => row.id === id);
  if (accounts.error || !account) {
    return (
      <Screen title="Bank account" back>
        <AppText tone={accounts.error ? 'negative' : 'muted'}>
          {accounts.error
            ? `Could not load this account: ${accounts.error.message}`
            : accounts.isPending
              ? 'Loading…'
              : 'This account no longer exists.'}
        </AppText>
      </Screen>
    );
  }
  const current = account;

  // Known only once everything that could use the account has loaded.
  const deletable =
    payments.data &&
    subscriptions.data &&
    personalSubscriptions.data &&
    !isInUse(current.id, payments.data, [...subscriptions.data, ...personalSubscriptions.data]);

  async function save(draft: BankAccountDraft) {
    const row = bankAccountRow(draft, current);
    await accountsRepository.save(await accountsRepository.build([row]));
    setToast((shown) => ({ id: (shown?.id ?? 0) + 1, text: 'Saved' }));
  }

  async function remove() {
    await accountsRepository.delete([current.id]);
    router.dismissTo(ownership === 'personal' ? '/personal' : '/joint');
  }

  return (
    <View style={styles.fill}>
      <Screen title={current.name} back>
        <Card title={`Balance over the last ${TREND_MONTHS} months`}>
          {payments.data ? (
            <BalanceChart points={dailyBalances(current, payments.data, today())} />
          ) : (
            <>
              <AppText variant="title" style={styles.figure}>
                {formatAmount(current.current_balance)}
              </AppText>
              <AppText tone={payments.error ? 'negative' : 'muted'}>
                {payments.error
                  ? `Could not load the payments: ${payments.error.message}`
                  : 'Loading…'}
              </AppText>
            </>
          )}
        </Card>

        <Card title="Details">
          <BankAccountForm
            key={current.id}
            account={current}
            quickButtons={
              (quickButtons.data ?? []).filter((button) => button.bank_account_id === current.id)
                .length
            }
            onSave={save}
            onDelete={deletable ? remove : undefined}
          />
        </Card>
      </Screen>
      <Toast toast={toast} onDismiss={dismissToast} />
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  figure: { fontVariant: ['tabular-nums'] },
});
