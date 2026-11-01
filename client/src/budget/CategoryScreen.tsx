import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet } from 'react-native';

import { CategoryForm } from '@/budget/CategoryForm';
import { categoryDraftRow, type CategoryDraft } from '@/budget/categoryDraft';
import { Figure, Figures } from '@/budget/Figures';
import { nearlySpent, paymentsCountedIn } from '@/budget/trackers';
import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ListRow } from '@/components/ListRow';
import { ProgressBar } from '@/components/ProgressBar';
import { Screen } from '@/components/Screen';
import { Sheet } from '@/components/Sheet';
import { today, type OwnershipType } from '@/domain/entities';
import { useRepositories, useRows } from '@/hooks/repositories';
import { formatAmount } from '@/theme/formatAmount';
import { formatDay, formatMonth } from '@/theme/formatDate';
import { SPACING } from '@/theme/tokens';

type CategoryScreenProps = { ownership: OwnershipType };

/**
 * One subcategory: its figures, the payments counted towards them, and its settings to edit. A
 * monthly subcategory counts this month's payments; a pot counts everything paid into it.
 */
export function CategoryScreen({ ownership }: CategoryScreenProps) {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const repositories = useRepositories();
  const categoriesRepository = repositories.categories(ownership);
  const categories = useRows(categoriesRepository);
  const payments = useRows(repositories.payments(ownership));
  const [editKey, setEditKey] = useState<number | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const closeEdit = useCallback(() => setEditOpen(false), []);

  const category = categories.data?.find((row) => row.id === id);
  const root = categories.data?.find((row) => row.id === category?.parent_id);
  if (categories.error || !category || !root) {
    return (
      <Screen title="Budget" back>
        <AppText tone={categories.error ? 'negative' : 'muted'}>
          {categories.error
            ? `Could not load this subcategory: ${categories.error.message}`
            : categories.isPending
              ? 'Loading…'
              : 'This subcategory no longer exists.'}
        </AppText>
      </Screen>
    );
  }

  const pot = category.accrual === 'multi_month';
  const now = today();
  const counted = paymentsCountedIn(payments.data ?? [], category, now);
  const total = counted.reduce((sum, payment) => sum + payment.expense, 0);
  const goalReached = pot && category.remaining <= 0;

  function edit() {
    setEditKey((current) => (current ?? 0) + 1);
    setEditOpen(true);
  }

  async function save(draft: CategoryDraft) {
    if (!category || !root) return;
    const row = categoryDraftRow(draft, root, pot, category);
    await categoriesRepository.save(await categoriesRepository.build([row]));
    closeEdit();
  }

  async function remove() {
    if (!category || !root) return;
    await categoriesRepository.delete([category.id]);
    closeEdit();
    router.dismissTo(
      ownership === 'personal'
        ? { pathname: '/personal/tracker/[id]', params: { id: root.id } }
        : { pathname: '/joint/tracker/[id]', params: { id: root.id } },
    );
  }

  return (
    <>
      <Screen
        title={category.name}
        back
        action={<Button title="Edit" variant="plain" onPress={edit} />}
      >
        <AppText tone="muted">{root.name}</AppText>
        <Card>
          {pot ? (
            <Figures>
              <Figure label="Cost" value={category.cost} />
              <Figure label="Saved" value={category.accrued} />
              <Figure label={goalReached ? 'Extra' : 'To go'} value={category.remaining} />
            </Figures>
          ) : (
            <Figures>
              <Figure label="Budget" value={category.budget} />
              <Figure label="Spent" value={category.accrued} />
              <Figure
                label={category.remaining < 0 ? 'Over budget' : 'Left'}
                value={category.remaining}
                negative={category.remaining < 0}
              />
            </Figures>
          )}
          <ProgressBar
            progress={category.progress / 100}
            warn={!pot && (nearlySpent(category) || category.remaining < 0)}
          />
          <AppText variant="caption" tone="muted">
            {pot
              ? `${formatAmount(category.budget)} planned this month${category.starting_balance ? ` · started with ${formatAmount(category.starting_balance)}` : ''}`
              : `${Math.round(category.progress)}% used · ${Math.round(category.split)}% of ${root.name}`}
          </AppText>
        </Card>

        <Card
          title={`${pot ? 'Paid in' : `Payments in ${formatMonth(now)}`}${counted.length > 0 ? ` · ${formatAmount(total)}` : ''}`}
          list
        >
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
              {pot ? 'Nothing paid in yet.' : 'No payments this month.'}
            </AppText>
          ) : (
            counted.map((payment) => (
              <ListRow
                key={payment.id}
                title={payment.name}
                subtitle={formatDay(payment.payment_date)}
                trailing={<Amount value={pot ? payment.expense : -payment.expense} signed />}
              />
            ))
          )}
        </Card>
      </Screen>

      <Sheet visible={editOpen} onClose={closeEdit} title={`Edit ${category.name}`}>
        {editKey !== null ? (
          <CategoryForm
            key={editKey}
            category={category}
            root={root}
            pot={pot}
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
  message: { padding: SPACING.lg },
});
