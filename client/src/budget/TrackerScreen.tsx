import { useLocalSearchParams, useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { BankItForm } from '@/budget/BankItForm';
import { BudgetRow } from '@/budget/BudgetRow';
import { BudgetForm, CategoryForm } from '@/budget/CategoryForm';
import { categoryDraftRow, trackerBudgetError, type CategoryDraft } from '@/budget/categoryDraft';
import { Figure, Figures } from '@/budget/Figures';
import { childrenOf, holdsPots, nearlySpent, takesSubcategories } from '@/budget/trackers';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ProgressBar } from '@/components/ProgressBar';
import { Screen } from '@/components/Screen';
import { Sheet } from '@/components/Sheet';
import { Toast, type ToastMessage } from '@/components/Toast';
import type { OwnershipType } from '@/domain/entities';
import type { CategoryView } from '@/domain/readModels';
import { useRepositories, useRows } from '@/hooks/repositories';
import { nameOptions } from '@/lookups';
import { formatAmount, parseAmount } from '@/theme/formatAmount';
import { SPACING } from '@/theme/tokens';
import { bankOneOffs } from '@/useCases/bankOneOffs';

type TrackerScreenProps = { ownership: OwnershipType };

/** What the sheet is for: the tracker's own budget, adding a subcategory, or banking pots. */
type SheetTarget = { kind: 'budget' } | { kind: 'new' } | { kind: 'bank' };

/** One budget tracker: its figures for the month, and the subcategories it is broken into. */
export function TrackerScreen({ ownership }: TrackerScreenProps) {
  const { id } = useLocalSearchParams<{ id: string }>();
  const repositories = useRepositories();
  const categoriesRepository = repositories.categories(ownership);
  const categories = useRows(categoriesRepository);
  const paymentsRepository = repositories.payments(ownership);
  const bankAccounts = useRows(repositories.bankAccounts(ownership));
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const dismissToast = useCallback(() => setToast(null), []);
  const router = useRouter();
  const [sheet, setSheet] = useState<{ target: SheetTarget; key: number } | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const closeSheet = useCallback(() => setSheetOpen(false), []);

  const tracker = categories.data?.find((category) => category.id === id);
  if (categories.error || !tracker) {
    return (
      <Screen title="Budget" back>
        <AppText tone={categories.error ? 'negative' : 'muted'}>
          {categories.error
            ? `Could not load this tracker: ${categories.error.message}`
            : categories.isPending
              ? 'Loading…'
              : 'This tracker no longer exists.'}
        </AppText>
      </Screen>
    );
  }

  const pots = holdsPots(tracker);
  const subcategories = childrenOf(categories.data ?? [], tracker.id);
  const adds = takesSubcategories(tracker);
  const allocated = subcategories.reduce((total, category) => total + category.budget, 0);
  const bankable = subcategories.filter((category) => category.budget > 0);

  function open(target: SheetTarget) {
    setSheet((current) => ({ target, key: (current?.key ?? 0) + 1 }));
    setSheetOpen(true);
  }

  async function addCategory(draft: CategoryDraft) {
    if (!tracker) return;
    const row = categoryDraftRow(draft, tracker, pots, null);
    await categoriesRepository.save(await categoriesRepository.build([row]));
    closeSheet();
  }

  function show(category: CategoryView) {
    router.push(
      ownership === 'personal'
        ? { pathname: '/personal/category/[id]', params: { id: category.id } }
        : { pathname: '/joint/category/[id]', params: { id: category.id } },
    );
  }

  async function saveBudget(text: string) {
    if (!tracker) return;
    const row = { ...tracker, budget: parseAmount(text) ?? 0 };
    await categoriesRepository.save(await categoriesRepository.build([row]));
    closeSheet();
  }

  async function bank(chosen: CategoryView[], bankAccountId: string) {
    const written = await bankOneOffs(paymentsRepository, chosen, bankAccountId);
    closeSheet();
    const total = written.reduce((sum, payment) => sum + payment.expense, 0);
    setToast((current) => ({ id: (current?.id ?? 0) + 1, text: `${formatAmount(total)} banked` }));
  }

  const target = sheet?.target;
  const sheetTitle =
    target?.kind === 'budget'
      ? `${tracker.name} budget`
      : target?.kind === 'bank'
        ? 'Bank it'
        : pots
          ? 'New pot'
          : 'New subcategory';

  return (
    <View style={styles.fill}>
      <Screen title={tracker.name} back>
        <Card>
          <Figures>
            <Figure label="Budget" value={tracker.budget} />
            <Figure label="Spent" value={tracker.accrued} />
            <Figure
              label={tracker.remaining < 0 ? 'Over budget' : 'Left'}
              value={tracker.remaining}
              negative={tracker.remaining < 0}
            />
          </Figures>
          <ProgressBar
            progress={tracker.progress / 100}
            warn={nearlySpent(tracker) || tracker.remaining < 0}
          />
          <AppText variant="caption" tone="muted">
            {Math.round(tracker.progress)}% used · {Math.round(tracker.split)}% of income
          </AppText>
          <Button
            title="Change budget"
            variant="secondary"
            onPress={() => open({ kind: 'budget' })}
          />
        </Card>

        {subcategories.length > 0 || adds ? (
          <Card
            title={
              subcategories.length > 0
                ? `${pots ? 'Pots' : 'Subcategories'} · ${formatAmount(allocated)} ${pots ? 'planned' : 'budgeted'}`
                : pots
                  ? 'Pots'
                  : 'Subcategories'
            }
            list
          >
            {subcategories.length === 0 ? (
              <AppText tone="muted" style={styles.empty}>
                {pots
                  ? 'No pots yet. Add one for something you’re saving up for.'
                  : 'No subcategories yet. Add one to break this tracker down.'}
              </AppText>
            ) : (
              subcategories.map((category) =>
                pots ? (
                  <BudgetRow
                    key={category.id}
                    title={category.name}
                    caption={`${formatAmount(category.accrued)} of ${formatAmount(category.cost)} saved · ${formatAmount(category.budget)} planned`}
                    left={category.remaining}
                    leftLabel="to go"
                    goal
                    progress={category.progress}
                    onPress={() => show(category)}
                  />
                ) : (
                  <BudgetRow
                    key={category.id}
                    title={category.name}
                    caption={`${formatAmount(category.accrued)} of ${formatAmount(category.budget)} spent · ${Math.round(category.split)}% of ${tracker.name}`}
                    left={category.remaining}
                    progress={category.progress}
                    warn={nearlySpent(category)}
                    onPress={() => show(category)}
                  />
                ),
              )
            )}
          </Card>
        ) : null}

        {pots && subcategories.length > 0 ? (
          <Button title="Bank it" onPress={() => open({ kind: 'bank' })} />
        ) : null}
        {adds ? (
          <Button
            title={pots ? 'Add a pot' : 'Add a subcategory'}
            variant="secondary"
            onPress={() => open({ kind: 'new' })}
          />
        ) : null}
      </Screen>

      <Sheet visible={sheetOpen} onClose={closeSheet} title={sheetTitle}>
        {target?.kind === 'budget' ? (
          <BudgetForm
            key={sheet?.key}
            tracker={tracker}
            validate={trackerBudgetError}
            onSave={saveBudget}
            onCancel={closeSheet}
          />
        ) : target?.kind === 'bank' ? (
          <BankItForm
            key={sheet?.key}
            pots={bankable}
            bankAccounts={nameOptions(bankAccounts.data ?? [])}
            onBank={bank}
            onCancel={closeSheet}
          />
        ) : target ? (
          <CategoryForm
            key={sheet?.key}
            category={null}
            root={tracker}
            pot={pots}
            onSave={addCategory}
            onDelete={() => Promise.resolve()}
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
  empty: { padding: SPACING.lg },
});
