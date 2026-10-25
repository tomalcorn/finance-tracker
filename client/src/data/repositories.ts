import type { CacheInvalidator } from '@/data/cache';
import type { TableGateway } from '@/data/gateway';
import {
  createRepository,
  type RepoContext,
  type RepoOwnership,
  type RepoSpec,
} from '@/data/repository';
import {
  BankAccountSchema,
  CategorySchema,
  IncomeSourceSchema,
  JointAccountSchema,
  JointAccountMemberSchema,
  type OwnershipType,
  PaymentSchema,
  QuickButtonSchema,
  SubscriptionSchema,
  UserSettingsSchema,
} from '@/domain/entities';
import {
  BankAccountViewSchema,
  CategoryViewSchema,
  IncomeSourceViewSchema,
  JointAccountMemberViewSchema,
  JointAccountViewSchema,
  PaymentViewSchema,
  QuickButtonViewSchema,
  SubscriptionViewSchema,
  UserSettingsViewSchema,
} from '@/domain/readModels';
import type { Repositories } from '@/ports/repositories';
import type { Repository } from '@/ports/repository';

/**
 * Build the user's repositories over a table gateway.
 *
 * The user's joint account (at most one) is read once, when a joint
 * repository first needs it, and shared by them all. A failed read is retried
 * on the next use.
 */
export function createRepositories(deps: {
  userId: string;
  gateway: TableGateway;
  cache: CacheInvalidator;
}): Repositories {
  let jointAccount: Promise<string | null> | undefined;
  const jointAccountId = () => {
    jointAccount ??= deps.gateway.select('joint_accounts', {}).then(
      (rows) => (typeof rows[0]?.id === 'string' ? rows[0].id : null),
      (error: unknown) => {
        jointAccount = undefined;
        throw error;
      },
    );
    return jointAccount;
  };

  const context = (ownership: RepoOwnership): RepoContext => ({
    ...deps,
    ownership,
    jointAccountId,
  });

  /**
   * For an aggregate split into personal and joint rows: a function giving the
   * repository for either half, each built on its first use.
   */
  function repositoryPerOwnership<EntityT extends object, ViewT>(spec: RepoSpec<EntityT, ViewT>) {
    const built = new Map<OwnershipType, Repository<EntityT, ViewT>>();
    return (ownership: OwnershipType) => {
      let repo = built.get(ownership);
      if (!repo) {
        repo = createRepository(spec, context(ownership));
        built.set(ownership, repo);
      }
      return repo;
    };
  }

  /** For an aggregate with no personal or joint split: a function giving its one repository. */
  function unownedRepository<EntityT extends object, ViewT>(spec: RepoSpec<EntityT, ViewT>) {
    let repo: Repository<EntityT, ViewT> | undefined;
    return () => (repo ??= createRepository(spec, context('unowned')));
  }

  return {
    bankAccounts: repositoryPerOwnership({
      entity: BankAccountSchema,
      view: BankAccountViewSchema,
      readFrom: 'bank_accounts_view',
      writeTo: 'bank_accounts',
    }),
    categories: repositoryPerOwnership({
      entity: CategorySchema,
      view: CategoryViewSchema,
      readFrom: 'categories_view',
      writeTo: 'categories',
    }),
    incomeSources: repositoryPerOwnership({
      entity: IncomeSourceSchema,
      view: IncomeSourceViewSchema,
      readFrom: 'income_sources_view',
      writeTo: 'income_sources',
    }),
    payments: repositoryPerOwnership({
      entity: PaymentSchema,
      view: PaymentViewSchema,
      readFrom: 'payments',
      writeTo: 'payments',
    }),
    quickButtons: repositoryPerOwnership({
      entity: QuickButtonSchema,
      view: QuickButtonViewSchema,
      readFrom: 'quick_buttons',
      writeTo: 'quick_buttons',
    }),
    subscriptions: repositoryPerOwnership({
      entity: SubscriptionSchema,
      view: SubscriptionViewSchema,
      readFrom: 'subscriptions_view',
      writeTo: 'subscriptions',
    }),
    userSettings: repositoryPerOwnership({
      entity: UserSettingsSchema,
      view: UserSettingsViewSchema,
      readFrom: 'user_settings',
      writeTo: 'user_settings',
    }),
    jointAccounts: unownedRepository({
      entity: JointAccountSchema,
      view: JointAccountViewSchema,
      readFrom: 'joint_accounts',
      writeTo: 'joint_accounts',
    }),
    jointAccountMembers: unownedRepository({
      entity: JointAccountMemberSchema,
      view: JointAccountMemberViewSchema,
      readFrom: 'joint_account_members',
      writeTo: 'joint_account_members',
    }),
  };
}
