import type { Guide } from '@/docs/guide';
import { bankAccounts } from '@/docs/guides/bankAccounts';
import { budgetTracker } from '@/docs/guides/budgetTracker';
import { financeAnalysis } from '@/docs/guides/financeAnalysis';
import { gettingStarted } from '@/docs/guides/gettingStarted';
import { jointAccounts } from '@/docs/guides/jointAccounts';
import { oneOffs } from '@/docs/guides/oneOffs';
import { payments } from '@/docs/guides/payments';
import { quickExpenses } from '@/docs/guides/quickExpenses';
import { subscriptions } from '@/docs/guides/subscriptions';

/** Every guide, in the order they are listed. */
export const GUIDES: readonly Guide[] = [
  gettingStarted,
  oneOffs,
  budgetTracker,
  payments,
  bankAccounts,
  subscriptions,
  financeAnalysis,
  jointAccounts,
  quickExpenses,
].sort((a, b) => a.order - b.order);

/** The guide at a slug, if there is one. */
export function guideBySlug(slug: string | undefined): Guide | undefined {
  return GUIDES.find((guide) => guide.slug === slug);
}
