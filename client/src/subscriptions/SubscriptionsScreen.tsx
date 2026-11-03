import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { Screen } from '@/components/Screen';
import { SegmentedControl } from '@/components/SegmentedControl';
import { Sheet } from '@/components/Sheet';
import { Toast, type ToastMessage } from '@/components/Toast';
import { today, type OwnershipType } from '@/domain/entities';
import type { SubscriptionView } from '@/domain/readModels';
import { useReconciliation, useRepositories, useRows } from '@/hooks/repositories';
import { categoryOptions, nameOptions } from '@/lookups';
import { SubscriptionForm } from '@/subscriptions/SubscriptionForm';
import { SubscriptionRow } from '@/subscriptions/SubscriptionRow';
import {
  CADENCES,
  subscriptionDraftOf,
  subscriptionRow,
  type SubscriptionDraft,
} from '@/subscriptions/subscriptionDraft';
import {
  bookedCount,
  isContribution,
  monthlyTotal,
  nextPaymentDate,
  notRunning,
  runningByCost,
  statusOf,
} from '@/subscriptions/subscriptionList';
import { formatAmount } from '@/theme/formatAmount';
import { formatDayOfMonth } from '@/theme/formatDate';

type Tab = 'subscriptions' | 'contributions';

const TABS: readonly { value: Tab; label: string }[] = [
  { value: 'subscriptions', label: 'Subscriptions' },
  { value: 'contributions', label: 'Joint contributions' },
];

type SubscriptionsScreenProps = { ownership: OwnershipType };

type SheetTarget = { subscription: SubscriptionView | null; draft: SubscriptionDraft };

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * Recurring payments, each opening to edit or delete. On the personal half, a member of a joint
 * account also gets their joint contributions, on a tab of their own. Without one, every row is in
 * the one list, so a leftover contribution can't go missing.
 */
export function SubscriptionsScreen({ ownership }: SubscriptionsScreenProps) {
  const repositories = useRepositories();
  const subscriptionsRepository = repositories.subscriptions(ownership);
  const subscriptions = useRows(subscriptionsRepository);
  const payments = useRows(repositories.payments(ownership));
  const bankAccounts = useRows(repositories.bankAccounts(ownership));
  const categories = useRows(repositories.categories(ownership));
  const jointAccounts = useRows(repositories.jointAccounts());
  const jointBankAccounts = useRows(repositories.bankAccounts('joint'));
  const jointIncomeSources = useRows(repositories.incomeSources('joint'));
  const reconciliation = useReconciliation();
  const [tab, setTab] = useState<Tab>('subscriptions');
  const [sheet, setSheet] = useState<(SheetTarget & { key: number }) | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const closeSheet = useCallback(() => setSheetOpen(false), []);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const dismissToast = useCallback(() => setToast(null), []);

  const now = today();
  const all = subscriptions.data ?? [];
  const tabbed = ownership === 'personal' && (jointAccounts.data?.length ?? 0) > 0;
  const onContributions = tabbed && tab === 'contributions';
  const shown = tabbed ? all.filter((row) => isContribution(row) === onContributions) : all;
  const running = runningByCost(shown, now);
  const stopped = notRunning(shown, now);
  const monthly = monthlyTotal(shown, now);
  const categoryChoices = categoryOptions(categories.data ?? []);
  const bankAccountOptions = nameOptions(bankAccounts.data ?? []);
  const jointCategoryId =
    categories.data?.find((row) => row.parent_id === null && row.name === 'Joint')?.id ?? null;

  function notify(text: string) {
    setToast((current) => ({ id: (current?.id ?? 0) + 1, text }));
  }

  function open(subscription: SubscriptionView | null) {
    const draft = subscriptionDraftOf(subscription, now);
    setSheet((current) => ({ subscription, draft, key: (current?.key ?? 0) + 1 }));
    setSheetOpen(true);
  }

  /** Book or remove the payments a change calls for. The change itself is already saved. */
  async function reconcile() {
    try {
      await repositories.reconcileSubscriptions(ownership);
    } catch (error) {
      notify(`Saved, but its payments couldn’t be updated: ${messageOf(error)}`);
    }
  }

  async function save(draft: SubscriptionDraft) {
    const editing = sheet?.subscription ?? null;
    const row = subscriptionRow(draft, editing, onContributions, jointCategoryId);
    await subscriptionsRepository.save(await subscriptionsRepository.build([row]));
    closeSheet();
    if (!editing) notify(`${draft.name.trim()} added`);
    await reconcile();
  }

  async function remove() {
    const subscription = sheet?.subscription;
    if (!subscription) return;
    await subscriptionsRepository.delete([subscription.id]);
    closeSheet();
    notify(`${subscription.name} deleted`);
  }

  /** What it actually charges and how often, whatever that comes to a month. */
  function charge(subscription: SubscriptionView): string {
    const cadence = CADENCES.find((option) => option.value === subscription.cadence)?.label ?? '';
    return `${formatAmount(subscription.amount)} ${cadence.toLowerCase()}`;
  }

  function describeRunning(subscription: SubscriptionView): string {
    const next = nextPaymentDate(payments.data ?? [], subscription.id, now);
    return next ? `${charge(subscription)} · next ${formatDayOfMonth(next)}` : charge(subscription);
  }

  function describeStopped(subscription: SubscriptionView): string {
    const status = statusOf(subscription, now) === 'ended' ? 'Ended' : 'Turned off';
    return `${status} · ${charge(subscription)}`;
  }

  const noun = onContributions ? 'joint contribution' : 'subscription';

  return (
    <View style={styles.fill}>
      <Screen title="Subscriptions" back>
        {reconciliation.error ? (
          <AppText tone="negative">
            Could not book the payments now due: {reconciliation.error.message}
          </AppText>
        ) : null}
        {tabbed ? (
          <SegmentedControl label="Show" value={tab} options={TABS} onChange={setTab} />
        ) : null}

        {subscriptions.error ? (
          <AppText tone="negative">
            Could not load your subscriptions: {subscriptions.error.message}
          </AppText>
        ) : subscriptions.isPending ? (
          <AppText tone="muted">Loading…</AppText>
        ) : shown.length === 0 ? (
          <Card>
            <AppText tone="muted">
              {onContributions
                ? 'No joint contributions yet. Add a standing order into the joint account.'
                : 'No subscriptions yet. Add one to book its payments for you.'}
            </AppText>
          </Card>
        ) : (
          <>
            {running.length > 0 ? (
              <>
                <Card>
                  <AppText variant="heading">{formatAmount(monthly)} a month</AppText>
                  <AppText tone="muted">{formatAmount(monthly * 12)} a year</AppText>
                </Card>
                <Card list>
                  {running.map((subscription) => (
                    <SubscriptionRow
                      key={subscription.id}
                      name={subscription.name}
                      caption={describeRunning(subscription)}
                      figure={`${formatAmount(subscription.monthly_cost)}/mo`}
                      share={monthly > 0 ? subscription.monthly_cost / monthly : 0}
                      onPress={() => open(subscription)}
                    />
                  ))}
                </Card>
              </>
            ) : null}
            {stopped.length > 0 ? (
              <Card title="Not running" list>
                {stopped.map((subscription) => (
                  <SubscriptionRow
                    key={subscription.id}
                    name={subscription.name}
                    caption={describeStopped(subscription)}
                    figure={formatAmount(subscription.amount)}
                    muted
                    onPress={() => open(subscription)}
                  />
                ))}
              </Card>
            ) : null}
          </>
        )}

        <Button title={`Add a ${noun}`} variant="secondary" onPress={() => open(null)} />
      </Screen>

      <Sheet
        visible={sheetOpen}
        onClose={closeSheet}
        title={sheet?.subscription ? `Edit ${sheet.subscription.name}` : `New ${noun}`}
      >
        {sheet ? (
          <SubscriptionForm
            key={sheet.key}
            subscription={sheet.subscription}
            initial={sheet.draft}
            contribution={onContributions}
            bankAccounts={bankAccountOptions}
            categories={categoryChoices}
            jointBankAccounts={nameOptions(jointBankAccounts.data ?? [])}
            jointIncomeSources={nameOptions(jointIncomeSources.data ?? [])}
            booked={
              sheet.subscription ? bookedCount(payments.data ?? [], sheet.subscription.id) : 0
            }
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

const styles = StyleSheet.create({
  fill: { flex: 1 },
});
