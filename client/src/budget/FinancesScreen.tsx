import { useRouter } from 'expo-router';
import { StyleSheet } from 'react-native';

import { AllocationBar, useTrackerColour } from '@/budget/AllocationBar';
import { BudgetRow } from '@/budget/BudgetRow';
import { nearlySpent, roots, totalIncome, trackerIcon } from '@/budget/trackers';
import { AppText } from '@/components/AppText';
import { Card } from '@/components/Card';
import { Screen } from '@/components/Screen';
import { today, type OwnershipType } from '@/domain/entities';
import { useRepositories, useRows } from '@/hooks/repositories';
import { filterPayments, monthOf, totals } from '@/payments/paymentList';
import { formatAmount } from '@/theme/formatAmount';
import { formatMonth } from '@/theme/formatDate';
import { SPACING } from '@/theme/tokens';

type FinancesScreenProps = { ownership: OwnershipType };

const TITLES: Record<OwnershipType, string> = { personal: 'Personal', joint: 'Joint' };

/**
 * One half of the finances: personal, or the joint account's. A user in no joint account sees an
 * explanation on the joint half instead.
 */
export function FinancesScreen({ ownership }: FinancesScreenProps) {
  const jointAccounts = useRows(useRepositories().jointAccounts());
  const account = jointAccounts.data?.[0];

  if (ownership === 'personal') {
    return (
      <Screen title={TITLES.personal}>
        <Overview ownership="personal" />
      </Screen>
    );
  }

  return (
    <Screen title={TITLES.joint}>
      {jointAccounts.error ? (
        <AppText tone="negative">
          Could not load your joint account: {jointAccounts.error.message}
        </AppText>
      ) : jointAccounts.isPending ? (
        <AppText tone="muted">Loading…</AppText>
      ) : account ? (
        <>
          <AppText tone="muted">Shared account · {account.name}</AppText>
          <Overview ownership="joint" />
        </>
      ) : (
        <Card>
          <AppText>You don’t have a joint account yet.</AppText>
          <AppText tone="muted">
            Once you’re a member of one, its shared budget shows here. Joint accounts are set up by
            hand for now: ask for one to be created, and say who should be on it.
          </AppText>
        </Card>
      )}
    </Screen>
  );
}

/**
 * The budget: income in, how it is split, a row per tracker opening its detail, and this month's
 * payments.
 */
function Overview({ ownership }: FinancesScreenProps) {
  const repositories = useRepositories();
  const router = useRouter();
  const colourOf = useTrackerColour();
  const categories = useRows(repositories.categories(ownership));
  const incomeSources = useRows(repositories.incomeSources(ownership));

  if (categories.error || incomeSources.error) {
    const error = categories.error ?? incomeSources.error;
    return <AppText tone="negative">Could not load your budget: {error?.message}</AppText>;
  }
  if (!categories.data || !incomeSources.data) return <AppText tone="muted">Loading…</AppText>;

  const trackers = roots(categories.data);
  const income = totalIncome(incomeSources.data);
  const lastMonth = incomeSources.data[0]?.income_roll_up_period === 'previous_month';

  function openPayments() {
    router.push(ownership === 'personal' ? '/personal/payments' : '/joint/payments');
  }

  function openAllocation() {
    router.push(ownership === 'personal' ? '/personal/allocation' : '/joint/allocation');
  }

  function open(id: string) {
    router.push(
      ownership === 'personal'
        ? { pathname: '/personal/tracker/[id]', params: { id } }
        : { pathname: '/joint/tracker/[id]', params: { id } },
    );
  }

  return (
    <>
      <Card title="Income split" label="Income split" onPress={openAllocation}>
        <AppText variant="heading">
          {formatAmount(income)}{' '}
          <AppText tone="muted">in {lastMonth ? 'last month' : 'this month'}</AppText>
        </AppText>
        <AllocationBar trackers={trackers} income={income} />
      </Card>

      <Card title="Budget trackers" list>
        {trackers.length === 0 ? (
          <AppText tone="muted" style={styles.empty}>
            No budget trackers yet.
          </AppText>
        ) : (
          trackers.map((tracker) => (
            <BudgetRow
              key={tracker.id}
              title={tracker.name}
              caption={`${formatAmount(tracker.accrued)} of ${formatAmount(tracker.budget)} spent`}
              left={tracker.remaining}
              progress={tracker.progress}
              warn={nearlySpent(tracker)}
              icon={trackerIcon(tracker.name)}
              iconColour={colourOf(tracker.name)}
              onPress={() => open(tracker.id)}
            />
          ))
        )}
      </Card>

      <PaymentsCard ownership={ownership} onPress={openPayments} />

      <AppText variant="caption" tone="muted">
        Bank accounts and subscriptions are still on the Streamlit app for now.
      </AppText>
    </>
  );
}

/** What went out and came in this month, and how much is still to check, opening the payments. */
function PaymentsCard({ ownership, onPress }: FinancesScreenProps & { onPress: () => void }) {
  const payments = useRows(useRepositories().payments(ownership));
  const now = today();
  const thisMonth = filterPayments(payments.data ?? [], {
    month: monthOf(now),
    kind: 'all',
    search: '',
  });
  const { out, in: incoming } = totals(thisMonth);
  const unchecked = thisMonth.filter((payment) => !payment.checked).length;

  return (
    <Card title="Payments" label="Payments" onPress={onPress}>
      {payments.error ? (
        <AppText tone="negative">Could not load your payments: {payments.error.message}</AppText>
      ) : payments.isPending ? (
        <AppText tone="muted">Loading…</AppText>
      ) : (
        <>
          <AppText variant="heading">
            {formatAmount(out)} <AppText tone="muted">out in {formatMonth(now)}</AppText>
          </AppText>
          <AppText tone="muted">
            {formatAmount(incoming)} in
            {unchecked > 0 ? ` · ${unchecked} not checked yet` : ''}
          </AppText>
        </>
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  empty: { padding: SPACING.lg },
});
