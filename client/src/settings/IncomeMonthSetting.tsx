import { useState } from 'react';

import { AppText } from '@/components/AppText';
import { SegmentedControl } from '@/components/SegmentedControl';
import type { IncomeRollUpPeriod, OwnershipType } from '@/domain/entities';
import { useRepositories, useRows } from '@/hooks/repositories';
import { useSubmit } from '@/hooks/submit';

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

/** Which month's income one half's budget is split against. A choice saves straight away. */
export function IncomeMonthSetting({ ownership, onSaved }: IncomeMonthSettingProps) {
  const repository = useRepositories().userSettings(ownership);
  const settings = useRows(repository);
  // One row per half is a database invariant, and first-run setup seeds it.
  const row = settings.data?.[0];
  const stored = row?.income_roll_up_period ?? 'current_month';
  const [chosen, setChosen] = useState<IncomeRollUpPeriod | null>(null);
  const { submit, saving, failure } = useSubmit(async (period: IncomeRollUpPeriod) => {
    await repository.save(await repository.build([{ ...row, income_roll_up_period: period }]));
    const label = PERIODS.find((option) => option.value === period)?.label.toLowerCase();
    onSaved(`${HALF_NAMES[ownership]} income now rolls up over ${label}.`);
  });
  const shown = saving && chosen ? chosen : stored;

  if (settings.error) {
    return <AppText tone="negative">Could not load this setting: {settings.error.message}</AppText>;
  }
  if (settings.isPending) return <AppText tone="muted">Loading…</AppText>;

  function choose(period: IncomeRollUpPeriod) {
    if (period === shown) return;
    setChosen(period);
    void submit(period);
  }

  return (
    <>
      <AppText variant="label">Income month</AppText>
      <SegmentedControl
        label={`${HALF_NAMES[ownership]} income month`}
        value={shown}
        options={PERIODS}
        onChange={choose}
      />
      <AppText variant="caption" tone="muted">
        Each budget tracker’s share of income is measured against the month chosen here. Spending is
        always totalled over the current month.
      </AppText>
      {failure ? (
        <AppText tone="negative">{`Could not save that setting: ${failure}`}</AppText>
      ) : null}
    </>
  );
}
