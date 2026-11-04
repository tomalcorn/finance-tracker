import { useState } from 'react';

import { AppText } from '@/components/AppText';
import { SegmentedControl } from '@/components/SegmentedControl';
import type { IncomeRollUpPeriod, OwnershipType } from '@/domain/entities';
import { useRepositories, useRows } from '@/hooks/repositories';

type IncomeMonthSettingProps = {
  ownership: OwnershipType;
  /** Reports a change once it has been saved. */
  onSaved: (text: string) => void;
};

const PERIODS: readonly { value: IncomeRollUpPeriod; label: string }[] = [
  { value: 'current_month', label: 'This month' },
  { value: 'previous_month', label: 'Last month' },
];

const HALF_NAMES: Record<OwnershipType, string> = { personal: 'Personal', joint: 'Joint' };

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Which month's income one half's budget is split against. A choice saves straight away. */
export function IncomeMonthSetting({ ownership, onSaved }: IncomeMonthSettingProps) {
  const repository = useRepositories().userSettings(ownership);
  const settings = useRows(repository);
  const [saving, setSaving] = useState<IncomeRollUpPeriod | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  // One row per half is a database invariant, and first-run setup seeds it.
  const row = settings.data?.[0];
  const stored = row?.income_roll_up_period ?? 'current_month';

  if (settings.error) {
    return <AppText tone="negative">Could not load this setting: {settings.error.message}</AppText>;
  }
  if (settings.isPending) return <AppText tone="muted">Loading…</AppText>;

  async function choose(period: IncomeRollUpPeriod) {
    if (period === (saving ?? stored)) return;
    setSaving(period);
    setFailure(null);
    try {
      await repository.save(await repository.build([{ ...row, income_roll_up_period: period }]));
      const label = PERIODS.find((option) => option.value === period)?.label.toLowerCase();
      onSaved(`${HALF_NAMES[ownership]} income now rolls up over ${label}.`);
    } catch (error) {
      setFailure(`Could not save that setting: ${messageOf(error)}`);
    } finally {
      setSaving(null);
    }
  }

  return (
    <>
      <AppText variant="label">Income month</AppText>
      <SegmentedControl
        label={`${HALF_NAMES[ownership]} income month`}
        value={saving ?? stored}
        options={PERIODS}
        onChange={(period) => void choose(period)}
      />
      <AppText variant="caption" tone="muted">
        Each budget tracker’s share of income is measured against the month chosen here. Spending is
        always totalled over the current month.
      </AppText>
      {failure ? <AppText tone="negative">{failure}</AppText> : null}
    </>
  );
}
