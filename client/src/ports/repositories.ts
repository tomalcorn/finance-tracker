import type {
  BankAccount,
  Category,
  IncomeSource,
  JointAccount,
  JointAccountMember,
  OwnershipType,
  Payment,
  QuickButton,
  Subscription,
  UserSettings,
} from '@/domain/entities';
import type {
  BankAccountView,
  CategoryView,
  IncomeSourceView,
  JointAccountMemberView,
  JointAccountView,
  PaymentView,
  QuickButtonView,
  SubscriptionView,
  UserSettingsView,
} from '@/domain/readModels';
import type { Repository } from '@/ports/repository';

/** Money moved from a personal account into the joint one, on one date. */
export type Contribution = {
  amount: number;
  fromBankAccountId: string;
  toBankAccountId: string;
  incomeSourceId: string;
  /** `YYYY-MM-DD`. */
  paymentDate: string;
};

/**
 * Every aggregate's repository for the signed-in user. An owned aggregate takes
 * the ownership half to serve; asking twice for the same half returns the same
 * repository.
 */
export type Repositories = {
  /** Whose rows these are. */
  userId: string;
  /**
   * Bring one half's subscriptions and their payments into line: book what is due, and remove
   * what no longer should be. Safe to run at any time.
   */
  reconcileSubscriptions(ownership: OwnershipType): Promise<void>;
  /**
   * Give one half whatever it is missing of its budget trackers and settings. What exists is left
   * alone, so it is safe to run at any time. Without a joint account the joint half has nothing to do.
   */
  initialiseWorkspace(ownership: OwnershipType): Promise<void>;
  /** Book a contribution in one go: a personal expense and a joint income, linked to each other. */
  contributeToJoint(contribution: Contribution): Promise<void>;
  bankAccounts(ownership: OwnershipType): Repository<BankAccount, BankAccountView>;
  categories(ownership: OwnershipType): Repository<Category, CategoryView>;
  incomeSources(ownership: OwnershipType): Repository<IncomeSource, IncomeSourceView>;
  payments(ownership: OwnershipType): Repository<Payment, PaymentView>;
  quickButtons(ownership: OwnershipType): Repository<QuickButton, QuickButtonView>;
  subscriptions(ownership: OwnershipType): Repository<Subscription, SubscriptionView>;
  userSettings(ownership: OwnershipType): Repository<UserSettings, UserSettingsView>;
  jointAccounts(): Repository<JointAccount, JointAccountView>;
  jointAccountMembers(): Repository<JointAccountMember, JointAccountMemberView>;
};
