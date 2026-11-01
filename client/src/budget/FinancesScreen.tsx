import { useRouter } from 'expo-router';
import { StyleSheet } from 'react-native';

import { AllocationBar, useTrackerColour } from '@/budget/AllocationBar';
import { BudgetRow } from '@/budget/BudgetRow';
import { nearlySpent, roots, totalIncome, trackerIcon } from '@/budget/trackers';
import { AppText } from '@/components/AppText';
import { Card } from '@/components/Card';
import { Screen } from '@/components/Screen';
import type { OwnershipType } from '@/domain/entities';
import { useRepositories, useRows } from '@/hooks/repositories';
import { formatAmount } from '@/theme/formatAmount';
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

/** The budget: income in, how it is split, and a row per tracker opening its detail. */
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

  function open(id: string) {
    router.push(
      ownership === 'personal'
        ? { pathname: '/personal/tracker/[id]', params: { id } }
        : { pathname: '/joint/tracker/[id]', params: { id } },
    );
  }

  return (
    <>
      <Card title="Income split">
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

      <AppText variant="caption" tone="muted">
        Income sources, payments, bank accounts and subscriptions are still on the Streamlit app for
        now.
      </AppText>
    </>
  );
}

const styles = StyleSheet.create({
  empty: { padding: SPACING.lg },
});
