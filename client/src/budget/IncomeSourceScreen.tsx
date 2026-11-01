import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet } from 'react-native';

import { IncomeSourceForm } from '@/budget/IncomeSourceForm';
import {
  fundedTrackers,
  hasPayments,
  incomeCountedIn,
  incomeSourceRow,
  rollUpDate,
  type IncomeSourceDraft,
} from '@/budget/incomeSources';
import { roots } from '@/budget/trackers';
import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ListRow } from '@/components/ListRow';
import { Screen } from '@/components/Screen';
import { Sheet } from '@/components/Sheet';
import { today, type OwnershipType } from '@/domain/entities';
import { useRepositories, useRows } from '@/hooks/repositories';
import { formatAmount } from '@/theme/formatAmount';
import { formatDay, formatMonth } from '@/theme/formatDate';
import { SPACING } from '@/theme/tokens';

type IncomeSourceScreenProps = { ownership: OwnershipType };

/** One income source: what it brought in for the budget month, the payments behind that, and Edit. */
export function IncomeSourceScreen({ ownership }: IncomeSourceScreenProps) {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const repositories = useRepositories();
  const sourcesRepository = repositories.incomeSources(ownership);
  const sources = useRows(sourcesRepository);
  const categories = useRows(repositories.categories(ownership));
  const payments = useRows(repositories.payments(ownership));
  const [editKey, setEditKey] = useState<number | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const closeEdit = useCallback(() => setEditOpen(false), []);

  const source = sources.data?.find((row) => row.id === id);
  if (sources.error || !source) {
    return (
      <Screen title="Income" back>
        <AppText tone={sources.error ? 'negative' : 'muted'}>
          {sources.error
            ? `Could not load this income source: ${sources.error.message}`
            : sources.isPending
              ? 'Loading…'
              : 'This income source no longer exists.'}
        </AppText>
      </Screen>
    );
  }

  const trackers = roots(categories.data ?? []);
  const funds = fundedTrackers(source, trackers);
  const month = formatMonth(rollUpDate(today(), source.income_roll_up_period));
  const counted = incomeCountedIn(payments.data ?? [], source, today());

  function edit() {
    setEditKey((current) => (current ?? 0) + 1);
    setEditOpen(true);
  }

  async function save(draft: IncomeSourceDraft) {
    if (!source) return;
    await sourcesRepository.save(await sourcesRepository.build([incomeSourceRow(draft, source)]));
    closeEdit();
  }

  async function remove() {
    if (!source) return;
    await sourcesRepository.delete([source.id]);
    closeEdit();
    router.dismissTo(ownership === 'personal' ? '/personal/allocation' : '/joint/allocation');
  }

  return (
    <>
      <Screen
        title={source.name}
        back
        action={<Button title="Edit" variant="plain" onPress={edit} />}
      >
        <Card>
          <AppText variant="caption" tone="muted">
            In {month}
          </AppText>
          <AppText variant="title" style={styles.amount}>
            {formatAmount(source.current_month)}
          </AppText>
          <AppText tone="muted">
            {funds.length > 0 ? `Funds ${funds.join(', ')}` : 'Funds no budget tracker yet'}
          </AppText>
        </Card>

        <Card title={`Payments in ${month}`} list>
          {payments.error ? (
            <AppText tone="negative" style={styles.message}>
              Could not load the payments: {payments.error.message}
            </AppText>
          ) : payments.isPending ? (
            <AppText tone="muted" style={styles.message}>
              Loading…
            </AppText>
          ) : counted.length === 0 ? (
            <AppText tone="muted" style={styles.message}>
              Nothing came in from it in {month}.
            </AppText>
          ) : (
            counted.map((payment) => (
              <ListRow
                key={payment.id}
                title={payment.name}
                subtitle={formatDay(payment.payment_date)}
                trailing={<Amount value={payment.income} signed />}
              />
            ))
          )}
        </Card>
      </Screen>

      <Sheet visible={editOpen} onClose={closeEdit} title={`Edit ${source.name}`}>
        {editKey !== null ? (
          <IncomeSourceForm
            key={editKey}
            source={source}
            trackers={trackers}
            deletable={!payments.isPending && !hasPayments(payments.data ?? [], source.id)}
            onSave={save}
            onDelete={remove}
            onCancel={closeEdit}
          />
        ) : null}
      </Sheet>
    </>
  );
}

const styles = StyleSheet.create({
  amount: { fontVariant: ['tabular-nums'] },
  message: { padding: SPACING.lg },
});
