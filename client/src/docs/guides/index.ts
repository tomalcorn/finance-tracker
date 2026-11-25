import type { Guide } from '@/docs/guide';
import { commonSituations } from '@/docs/guides/commonSituations';
import { gettingStarted } from '@/docs/guides/gettingStarted';
import { jointAccounts } from '@/docs/guides/jointAccounts';

/** Every guide, in the order they are listed. */
export const GUIDES: readonly Guide[] = [gettingStarted, commonSituations, jointAccounts].sort(
  (a, b) => a.order - b.order,
);

/** The guide at a slug, if there is one. */
export function guideBySlug(slug: string | undefined): Guide | undefined {
  return GUIDES.find((guide) => guide.slug === slug);
}
