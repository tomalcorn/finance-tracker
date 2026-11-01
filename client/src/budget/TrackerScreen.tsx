import { useLocalSearchParams } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { BudgetRow } from '@/budget/BudgetRow';
import { BudgetForm, CategoryForm } from '@/budget/CategoryForm';
import { categoryDraftRow, trackerBudgetError, type CategoryDraft } from '@/budget/categoryDraft';
import { childrenOf, holdsPots, nearlySpent, takesSubcategories } from '@/budget/trackers';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ProgressBar } from '@/components/ProgressBar';
import { Screen } from '@/components/Screen';
import { Sheet } from '@/components/Sheet';
import type { OwnershipType } from '@/domain/entities';
import type { CategoryView } from '@/domain/readModels';
import { useRepositories, useRows } from '@/hooks/repositories';
import { formatAmount, parseAmount } from '@/theme/formatAmount';
import { SPACING } from '@/theme/tokens';

type TrackerScreenProps = { ownership: OwnershipType };

/** What the sheet is editing: the tracker's own budget, or one of its subcategories. */
type SheetTarget = { kind: 'budget' } | { kind: 'category'; category: CategoryView | null };

/** One budget tracker: its figures for the month, and the subcategories it is broken into. */
export function TrackerScreen({ ownership }: TrackerScreenProps) {
  const { id } = useLocalSearchParams<{ id: string }>();
  const categoriesRepository = useRepositories().categories(ownership);
  const categories = useRows(categoriesRepository);
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

  function open(target: SheetTarget) {
    setSheet((current) => ({ target, key: (current?.key ?? 0) + 1 }));
    setSheetOpen(true);
  }

  async function saveCategory(draft: CategoryDraft, category: CategoryView | null) {
    if (!tracker) return;
    const row = categoryDraftRow(draft, tracker, pots, category);
    await categoriesRepository.save(await categoriesRepository.build([row]));
    closeSheet();
  }

  async function deleteCategory(category: CategoryView) {
    await categoriesRepository.delete([category.id]);
    closeSheet();
  }

  async function saveBudget(text: string) {
    if (!tracker) return;
    const row = { ...tracker, budget: parseAmount(text) ?? 0 };
    await categoriesRepository.save(await categoriesRepository.build([row]));
    closeSheet();
  }

  const target = sheet?.target;
  const editing = target?.kind === 'category' ? target.category : null;
  const sheetTitle =
    target?.kind === 'budget'
      ? `${tracker.name} budget`
      : editing
        ? `Edit ${editing.name}`
        : pots
          ? 'New pot'
          : 'New subcategory';

  return (
    <>
      <Screen title={tracker.name} back>
        <Card>
          <View style={styles.figures}>
            <Figure label="Budget" value={tracker.budget} />
            <Figure label="Spent" value={tracker.accrued} />
            <Figure
              label={tracker.remaining < 0 ? 'Over budget' : 'Left'}
              value={tracker.remaining}
              negative={tracker.remaining < 0}
            />
          </View>
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
                    onPress={() => open({ kind: 'category', category })}
                  />
                ) : (
                  <BudgetRow
                    key={category.id}
                    title={category.name}
                    caption={`${formatAmount(category.accrued)} of ${formatAmount(category.budget)} spent · ${Math.round(category.split)}% of ${tracker.name}`}
                    left={category.remaining}
                    progress={category.progress}
                    warn={nearlySpent(category)}
                    onPress={() => open({ kind: 'category', category })}
                  />
                ),
              )
            )}
          </Card>
        ) : null}

        {adds ? (
          <Button
            title={pots ? 'Add a pot' : 'Add a subcategory'}
            variant="secondary"
            onPress={() => open({ kind: 'category', category: null })}
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
        ) : target ? (
          <CategoryForm
            key={sheet?.key}
            category={editing}
            root={tracker}
            pot={pots}
            onSave={(draft) => saveCategory(draft, editing)}
            onDelete={() => (editing ? deleteCategory(editing) : Promise.resolve())}
            onCancel={closeSheet}
          />
        ) : null}
      </Sheet>
    </>
  );
}

/** One headline figure: a small label over an amount. */
function Figure({
  label,
  value,
  negative = false,
}: {
  label: string;
  value: number;
  negative?: boolean;
}) {
  return (
    <View
      accessible
      aria-label={`${formatAmount(Math.abs(value))} ${label.toLowerCase()}`}
      style={styles.figure}
    >
      <AppText variant="caption" tone="muted">
        {label}
      </AppText>
      <AppText variant="heading" tone={negative ? 'negative' : 'default'} style={styles.amount}>
        {formatAmount(Math.abs(value))}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  figures: { flexDirection: 'row', gap: SPACING.md },
  figure: { flex: 1, gap: 2 },
  amount: { fontVariant: ['tabular-nums'] },
  empty: { padding: SPACING.lg },
});
