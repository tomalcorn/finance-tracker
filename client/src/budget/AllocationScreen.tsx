import { useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';

import { useTrackerColour } from '@/budget/AllocationBar';
import { AllocationRing } from '@/budget/AllocationRing';
import { IncomeSourceForm } from '@/budget/IncomeSourceForm';
import { fundedTrackers, incomeSourceRow, type IncomeSourceDraft } from '@/budget/incomeSources';
import { changedRows, draftBudget, editErrors, type BudgetEdits } from '@/budget/rebalance';
import { roots, totalIncome } from '@/budget/trackers';
import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ListRow } from '@/components/ListRow';
import { Screen } from '@/components/Screen';
import { Sheet } from '@/components/Sheet';
import { Toast, type ToastMessage } from '@/components/Toast';
import type { OwnershipType } from '@/domain/entities';
import type { CategoryView } from '@/domain/readModels';
import { useRepositories, useRows } from '@/hooks/repositories';
import { useAppTheme } from '@/theme/theme';
import { formatAmount } from '@/theme/formatAmount';
import { RADIUS, SPACING, TYPOGRAPHY } from '@/theme/tokens';

type AllocationScreenProps = { ownership: OwnershipType };

/**
 * The month's income split between the budget trackers, to rebalance them against it: a ring that
 * follows the budgets as they are typed, one budget per tracker, saved together, and the income
 * sources the split is made from.
 */
export function AllocationScreen({ ownership }: AllocationScreenProps) {
  const repositories = useRepositories();
  const categoriesRepository = repositories.categories(ownership);
  const categories = useRows(categoriesRepository);
  const sourcesRepository = repositories.incomeSources(ownership);
  const incomeSources = useRows(sourcesRepository);
  const router = useRouter();
  const [sourceKey, setSourceKey] = useState<number | null>(null);
  const [sourceOpen, setSourceOpen] = useState(false);
  const closeSource = useCallback(() => setSourceOpen(false), []);
  const [edits, setEdits] = useState<BudgetEdits>({});
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const dismissToast = useCallback(() => setToast(null), []);

  if (categories.error || incomeSources.error) {
    const error = categories.error ?? incomeSources.error;
    return (
      <Screen title="Income split" back>
        <AppText tone="negative">Could not load your budget: {error?.message}</AppText>
      </Screen>
    );
  }
  if (!categories.data || !incomeSources.data) {
    return (
      <Screen title="Income split" back>
        <AppText tone="muted">Loading…</AppText>
      </Screen>
    );
  }

  const trackers = roots(categories.data);
  const income = totalIncome(incomeSources.data);
  const lastMonth = incomeSources.data[0]?.income_roll_up_period === 'previous_month';
  const slices = trackers.map((tracker) => ({
    key: tracker.id,
    name: tracker.name,
    budget: draftBudget(tracker, edits),
  }));
  const errors = editErrors(edits);
  const changes = changedRows(trackers, edits);
  const editing = Object.keys(edits).length > 0;

  function showSource(id: string) {
    router.push(
      ownership === 'personal'
        ? { pathname: '/personal/income/[id]', params: { id } }
        : { pathname: '/joint/income/[id]', params: { id } },
    );
  }

  function addSource() {
    setSourceKey((current) => (current ?? 0) + 1);
    setSourceOpen(true);
  }

  async function saveSource(draft: IncomeSourceDraft) {
    await sourcesRepository.save(await sourcesRepository.build([incomeSourceRow(draft, null)]));
    closeSource();
    setToast((current) => ({ id: (current?.id ?? 0) + 1, text: `${draft.name.trim()} added` }));
  }

  async function save() {
    setSaving(true);
    setFailure(null);
    try {
      await categoriesRepository.save(await categoriesRepository.build(changes));
      setEdits({});
      setToast((current) => ({ id: (current?.id ?? 0) + 1, text: 'Budgets saved' }));
    } catch (error) {
      setFailure(error instanceof Error ? error.message : String(error));
    } finally {
      setSaving(false);
    }
  }

  return (
    <View style={styles.fill}>
      <Screen title="Income split" back>
        <AppText variant="heading">
          {formatAmount(income)}{' '}
          <AppText tone="muted">in {lastMonth ? 'last month' : 'this month'}</AppText>
        </AppText>
        <AllocationRing slices={slices} income={income} />

        <Card title="Monthly budgets" list>
          {trackers.map((tracker) => (
            <BudgetLine
              key={tracker.id}
              tracker={tracker}
              text={edits[tracker.id] ?? tracker.budget.toFixed(2)}
              budget={draftBudget(tracker, edits)}
              income={income}
              error={errors[tracker.id]}
              onChange={(text) => setEdits((current) => ({ ...current, [tracker.id]: text }))}
            />
          ))}
        </Card>

        {failure ? <AppText tone="negative">{failure}</AppText> : null}
        <Button
          title="Save budgets"
          onPress={() => void save()}
          disabled={saving || changes.length === 0 || Object.keys(errors).length > 0}
        />
        {editing ? (
          <Button title="Undo changes" variant="plain" onPress={() => setEdits({})} />
        ) : null}

        <Card title="Income sources" list>
          {incomeSources.data.length === 0 ? (
            <AppText tone="muted" style={styles.message}>
              No income sources yet. Add one for each place money comes in from.
            </AppText>
          ) : (
            [...incomeSources.data]
              .sort((a, b) => b.current_month - a.current_month || a.name.localeCompare(b.name))
              .map((source) => {
                const funds = fundedTrackers(source, trackers);
                return (
                  <ListRow
                    key={source.id}
                    title={source.name}
                    subtitle={funds.length > 0 ? `Funds ${funds.join(', ')}` : 'Funds nothing yet'}
                    trailing={<Amount value={source.current_month} />}
                    onPress={() => showSource(source.id)}
                  />
                );
              })
          )}
        </Card>
        <Button title="Add an income source" variant="secondary" onPress={addSource} />
      </Screen>

      <Sheet visible={sourceOpen} onClose={closeSource} title="New income source">
        {sourceKey !== null ? (
          <IncomeSourceForm
            key={sourceKey}
            source={null}
            trackers={trackers}
            deletable={false}
            onSave={saveSource}
            onDelete={() => Promise.resolve()}
            onCancel={closeSource}
          />
        ) : null}
      </Sheet>
      <Toast toast={toast} onDismiss={dismissToast} />
    </View>
  );
}

type BudgetLineProps = {
  tracker: CategoryView;
  /** The budget as typed. */
  text: string;
  /** The budget as it stands with the edits, for its share of income. */
  budget: number;
  income: number;
  error?: string;
  onChange: (text: string) => void;
};

/** One tracker's budget to rebalance: its colour, name and spend, and the amount to edit. */
function BudgetLine({ tracker, text, budget, income, error, onChange }: BudgetLineProps) {
  const { colors } = useAppTheme();
  const colourOf = useTrackerColour();
  const share = income > 0 ? Math.round((budget / income) * 100) : 0;

  return (
    <View style={styles.line}>
      <View style={[styles.swatch, { backgroundColor: colourOf(tracker.name) }]} />
      <View style={styles.name}>
        <AppText numberOfLines={1}>{tracker.name}</AppText>
        <AppText variant="caption" tone={error ? 'negative' : 'muted'} numberOfLines={1}>
          {error ?? `${share}% · ${formatAmount(tracker.accrued)} spent`}
        </AppText>
      </View>
      <TextInput
        aria-label={`${tracker.name} budget`}
        aria-invalid={error ? true : undefined}
        value={text}
        onChangeText={onChange}
        inputMode="decimal"
        selectTextOnFocus
        style={[
          TYPOGRAPHY.body,
          styles.input,
          {
            color: colors.text,
            backgroundColor: colors.surfaceMuted,
            borderColor: error ? colors.negative : 'transparent',
          },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  message: { padding: SPACING.lg },
  line: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
  },
  swatch: { width: 10, height: 10, borderRadius: RADIUS.pill },
  name: { flex: 1, gap: 2 },
  input: {
    width: 112,
    minHeight: 40,
    paddingHorizontal: SPACING.md,
    borderRadius: RADIUS.md,
    borderWidth: 1.5,
    textAlign: 'right',
    fontVariant: ['tabular-nums'],
  },
});
