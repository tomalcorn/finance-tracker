import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { ContributeForm } from '@/contributions/ContributeForm';
import { useRepositories, useRows } from '@/hooks/repositories';
import { nameOptions } from '@/lookups';
import type { Contribution } from '@/ports/repositories';

type ContributeSheetContentProps = {
  onContribute: (contribution: Contribution) => Promise<void>;
  onCancel: () => void;
};

/** The contribution form, once both halves' accounts and the joint income sources have loaded. */
export function ContributeSheetContent({ onContribute, onCancel }: ContributeSheetContentProps) {
  const repositories = useRepositories();
  const personalAccounts = useRows(repositories.bankAccounts('personal'));
  const jointAccounts = useRows(repositories.bankAccounts('joint'));
  const incomeSources = useRows(repositories.incomeSources('joint'));

  const error = personalAccounts.error ?? jointAccounts.error ?? incomeSources.error;
  if (error) {
    return (
      <>
        <AppText tone="negative">Could not load your accounts: {error.message}</AppText>
        <Button title="Close" variant="plain" onPress={onCancel} />
      </>
    );
  }
  if (!personalAccounts.data || !jointAccounts.data || !incomeSources.data) {
    return <AppText tone="muted">Loading…</AppText>;
  }
  return (
    <ContributeForm
      personalAccounts={nameOptions(personalAccounts.data)}
      jointAccounts={nameOptions(jointAccounts.data)}
      incomeSources={nameOptions(incomeSources.data)}
      onContribute={onContribute}
      onCancel={onCancel}
    />
  );
}
