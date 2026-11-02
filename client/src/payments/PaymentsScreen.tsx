import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { useCallback, useRef, useState } from 'react';
import { Pressable, StyleSheet, TextInput, View } from 'react-native';

import { Figure, Figures } from '@/budget/Figures';
import { AppText } from '@/components/AppText';
import { Card } from '@/components/Card';
import { interactiveBackground } from '@/components/interaction';
import { Screen } from '@/components/Screen';
import { SegmentedControl } from '@/components/SegmentedControl';
import { Sheet } from '@/components/Sheet';
import { TextField } from '@/components/TextField';
import { Toast, type ToastMessage } from '@/components/Toast';
import { today, type OwnershipType } from '@/domain/entities';
import type { PaymentView } from '@/domain/readModels';
import { useRepositories, useRows } from '@/hooks/repositories';
import { categoryOptions, nameOptions } from '@/lookups';
import { CategoryGroup } from '@/payments/CategoryGroup';
import { PaymentForm } from '@/payments/PaymentForm';
import { PaymentRow } from '@/payments/PaymentRow';
import { SearchSuggestions } from '@/payments/SearchSuggestions';
import { useOptimisticChecks } from '@/payments/useOptimisticChecks';
import { paymentDraftOf, paymentRow, type PaymentDraft } from '@/payments/paymentDraft';
import {
  byCategory,
  byDay,
  closingBalances,
  filterPayments,
  monthOf,
  shiftMonth,
  totals,
  type PaymentKind,
} from '@/payments/paymentList';
import {
  matchesSearch,
  parseSearch,
  paymentSearchFields,
  searchSuggestions,
  type SearchSuggestion,
} from '@/payments/paymentSearch';
import { useAppTheme } from '@/theme/theme';
import { formatAmount } from '@/theme/formatAmount';
import { formatDay, formatMonthYear } from '@/theme/formatDate';
import { RADIUS, SPACING } from '@/theme/tokens';

const KINDS: readonly { value: PaymentKind; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'expense', label: 'Out' },
  { value: 'income', label: 'In' },
];

/** How the month is laid out: a list of days, or what was spent in each category. */
type Layout = 'days' | 'categories';

const LAYOUTS: readonly { value: Layout; label: string }[] = [
  { value: 'days', label: 'By day' },
  { value: 'categories', label: 'By category' },
];

const PREVIOUS: SymbolViewProps['name'] = { ios: 'chevron.left', web: 'chevron_left' };
const NEXT: SymbolViewProps['name'] = { ios: 'chevron.right', web: 'chevron_right' };
const PLUS: SymbolViewProps['name'] = { ios: 'plus', web: 'add' };

type PaymentsScreenProps = { ownership: OwnershipType };

type SheetTarget = { payment: PaymentView | null; draft: PaymentDraft };

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * A month of payments, money out and in, grouped by day with the newest first, or the money out
 * broken down by category, the most spent first. Each payment can be ticked as checked from the
 * list, or opened to edit or delete; Add opens an empty one.
 */
export function PaymentsScreen({ ownership }: PaymentsScreenProps) {
  const repositories = useRepositories();
  const paymentsRepository = repositories.payments(ownership);
  const payments = useRows(paymentsRepository);
  const bankAccounts = useRows(repositories.bankAccounts(ownership));
  const categories = useRows(repositories.categories(ownership));
  const incomeSources = useRows(repositories.incomeSources(ownership));
  const [month, setMonth] = useState(() => monthOf(today()));
  const [layout, setLayout] = useState<Layout>('days');
  const [kind, setKind] = useState<PaymentKind>('all');
  const [expanded, setExpanded] = useState<ReadonlySet<string | null>>(() => new Set());
  const [search, setSearch] = useState('');
  const searchBox = useRef<TextInput>(null);
  const [sheet, setSheet] = useState<(SheetTarget & { key: number }) | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const closeSheet = useCallback(() => setSheetOpen(false), []);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const dismissToast = useCallback(() => setToast(null), []);
  const checks = useOptimisticChecks(
    async (payment, checked) => {
      await paymentsRepository.save(await paymentsRepository.build([{ ...payment, checked }]));
    },
    (payment, error) => notify(`Could not update ${payment.name}: ${messageOf(error)}`),
  );

  const bankAccountOptions = nameOptions(bankAccounts.data ?? []);
  const categoryChoices = categoryOptions(categories.data ?? []);
  const incomeSourceOptions = nameOptions(incomeSources.data ?? []);
  const labels = new Map(
    [...bankAccountOptions, ...categoryChoices, ...incomeSourceOptions].map((option) => [
      option.value,
      option.label,
    ]),
  );

  function describe(payment: PaymentView): string {
    const source =
      payment.payment_type === 'income' ? payment.income_source_id : payment.category_id;
    return [source, payment.bank_account_id]
      .map((id) => (id ? labels.get(id) : undefined))
      .filter((label) => label !== undefined)
      .join(' · ');
  }

  /** A payment in its category's group, which already names the category. */
  function describeInCategory(payment: PaymentView): string {
    const account = labels.get(payment.bank_account_id);
    return [formatDay(payment.payment_date), account].filter(Boolean).join(' · ');
  }

  function toggleGroup(categoryId: string | null) {
    setExpanded((current) => {
      const next = new Set(current);
      if (!next.delete(categoryId)) next.add(categoryId);
      return next;
    });
  }

  const all = checks.applyTo(payments.data ?? []);
  const inMonth = filterPayments(all, { month, kind: 'all' });
  const searchFields = paymentSearchFields({
    names: [...new Set(inMonth.map((payment) => payment.name))],
    bankAccounts: bankAccountOptions.map((option) => option.label),
    categories: categoryChoices.map((option) => option.label),
    incomeSources: incomeSourceOptions.map((option) => option.label),
    labelOf: (id) => labels.get(id),
  });
  const parsedSearch = parseSearch(search, searchFields);
  const suggestions = searchSuggestions(search, searchFields);
  const byCategories = layout === 'categories';
  const shown = filterPayments(all, { month, kind: byCategories ? 'expense' : kind }, (payment) =>
    matchesSearch(payment, parsedSearch, describe),
  );
  const days = byDay(shown);
  const groups = byCategory(shown);
  const spent = groups.reduce((sum, group) => sum + group.total, 0);
  const monthTotals = totals(inMonth);
  const monthDate = `${month}-01`;

  function chooseSuggestion(suggestion: SearchSuggestion | undefined) {
    if (!suggestion) return;
    setSearch(suggestion.query);
    searchBox.current?.focus();
  }

  function notify(text: string) {
    setToast((current) => ({ id: (current?.id ?? 0) + 1, text }));
  }

  function open(payment: PaymentView | null) {
    const draft = paymentDraftOf(payment, monthOf(today()) === month ? today() : monthDate);
    setSheet((current) => ({ payment, draft, key: (current?.key ?? 0) + 1 }));
    setSheetOpen(true);
  }

  async function save(draft: PaymentDraft) {
    const editing = sheet?.payment ?? null;
    const row = paymentRow(draft, editing);
    await paymentsRepository.save(await paymentsRepository.build([row]));
    closeSheet();
    setMonth(monthOf(draft.date));
    if (!editing) notify(`${draft.name.trim()} added`);
  }

  async function remove() {
    const payment = sheet?.payment;
    if (!payment) return;
    await paymentsRepository.delete([payment.id]);
    closeSheet();
    notify(`${payment.name} deleted`);
  }

  const lookupError = bankAccounts.error ?? categories.error ?? incomeSources.error;
  const searching = search.trim() !== '' || (!byCategories && kind !== 'all');

  return (
    <View style={styles.fill}>
      <Screen title="Payments" back>
        <Card>
          <View style={styles.stepper}>
            <MonthButton
              icon={PREVIOUS}
              label="Previous month"
              onPress={() => setMonth((current) => shiftMonth(current, -1))}
            />
            <AppText variant="heading" style={styles.month} aria-live="polite">
              {formatMonthYear(monthDate)}
            </AppText>
            <MonthButton
              icon={NEXT}
              label="Next month"
              onPress={() => setMonth((current) => shiftMonth(current, 1))}
            />
          </View>
          <Figures>
            <Figure label="Out" value={monthTotals.out} />
            <Figure label="In" value={monthTotals.in} />
          </Figures>
        </Card>

        <SegmentedControl label="Group" value={layout} options={LAYOUTS} onChange={setLayout} />
        {byCategories ? (
          <AppText variant="caption" tone="muted">
            Money out, by the budget tracker or category it came out of.
          </AppText>
        ) : (
          <SegmentedControl label="Show" value={kind} options={KINDS} onChange={setKind} />
        )}
        <View style={styles.searchRow}>
          <View style={styles.searchField}>
            <TextField
              ref={searchBox}
              label="Search"
              value={search}
              onChangeText={setSearch}
              onSubmitEditing={() => chooseSuggestion(suggestions[0])}
              placeholder="Search, or type @ to filter"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>
          <AddTile onPress={() => open(null)} />
        </View>
        <SearchSuggestions suggestions={suggestions} onChoose={chooseSuggestion} />

        {lookupError ? (
          <AppText tone="negative">Could not load the names: {lookupError.message}</AppText>
        ) : null}
        {payments.error ? (
          <AppText tone="negative">Could not load your payments: {payments.error.message}</AppText>
        ) : payments.isPending ? (
          <AppText tone="muted">Loading…</AppText>
        ) : shown.length === 0 ? (
          <Card>
            <AppText tone="muted">
              {searching
                ? 'Nothing here matches.'
                : byCategories
                  ? `Nothing spent in ${formatMonthYear(monthDate)}.`
                  : `No payments in ${formatMonthYear(monthDate)}. Add one to start.`}
            </AppText>
          </Card>
        ) : byCategories ? (
          <Card list>
            {groups.map((group) => (
              <CategoryGroup
                key={group.categoryId ?? ''}
                group={group}
                label={
                  group.categoryId === null
                    ? 'No category'
                    : (labels.get(group.categoryId) ?? 'Unknown category')
                }
                spent={spent}
                expanded={expanded.has(group.categoryId)}
                onToggle={() => toggleGroup(group.categoryId)}
                describe={describeInCategory}
                onOpenPayment={open}
                onToggleChecked={(payment) => void checks.toggle(payment)}
              />
            ))}
          </Card>
        ) : (
          days.map((day) => (
            <Card
              key={day.date}
              title={`${formatDay(day.date)} · ${formatAmount(day.net)}`}
              titleDetail={closingBalances(day, bankAccounts.data ?? [], all)
                .map(({ name, balance }) => `${name} ${formatAmount(balance)}`)
                .join(' · ')}
              list
            >
              {day.payments.map((payment) => (
                <PaymentRow
                  key={payment.id}
                  payment={payment}
                  subtitle={describe(payment)}
                  onPress={() => open(payment)}
                  onToggleChecked={() => void checks.toggle(payment)}
                />
              ))}
            </Card>
          ))
        )}
      </Screen>

      <Sheet
        visible={sheetOpen}
        onClose={closeSheet}
        title={sheet?.payment ? `Edit ${sheet.payment.name}` : 'New payment'}
      >
        {sheet ? (
          <PaymentForm
            key={sheet.key}
            payment={sheet.payment}
            initial={sheet.draft}
            bankAccounts={bankAccountOptions}
            categories={categoryChoices}
            incomeSources={incomeSourceOptions}
            onSave={save}
            onDelete={remove}
            onCancel={closeSheet}
          />
        ) : null}
      </Sheet>
      <Toast toast={toast} onDismiss={dismissToast} />
    </View>
  );
}

/** The tile beside the search that starts a new payment. */
function AddTile({ onPress }: { onPress: () => void }) {
  const { colors } = useAppTheme();
  return (
    <Pressable
      role="button"
      aria-label="Add"
      onPress={onPress}
      style={({ pressed }) => [
        styles.addTile,
        { backgroundColor: colors.accent, opacity: pressed ? 0.8 : 1 },
      ]}
    >
      <SymbolView name={PLUS} size={18} tintColor={colors.onAccent} />
      <AppText variant="label" style={{ color: colors.onAccent }}>
        Add
      </AppText>
    </Pressable>
  );
}

type MonthButtonProps = { icon: SymbolViewProps['name']; label: string; onPress: () => void };

/** A round button stepping the month back or on. */
function MonthButton({ icon, label, onPress }: MonthButtonProps) {
  const { colors } = useAppTheme();
  return (
    <Pressable
      role="button"
      aria-label={label}
      onPress={onPress}
      hitSlop={SPACING.xs}
      style={(state) => [
        styles.monthButton,
        { backgroundColor: interactiveBackground(state, colors, colors.surfaceMuted) },
      ]}
    >
      <SymbolView name={icon} size={18} tintColor={colors.text} />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  searchRow: { flexDirection: 'row', alignItems: 'flex-end', gap: SPACING.md },
  searchField: { flex: 1 },
  addTile: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: SPACING.xs,
    paddingHorizontal: SPACING.md,
    borderRadius: RADIUS.md,
  },
  stepper: { flexDirection: 'row', alignItems: 'center', gap: SPACING.md },
  month: { flex: 1, textAlign: 'center' },
  monthButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
