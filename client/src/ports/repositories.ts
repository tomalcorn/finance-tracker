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

/**
 * Every aggregate's repository for the signed-in user. An owned aggregate takes
 * the ownership half to serve; asking twice for the same half returns the same
 * repository.
 */
export type Repositories = {
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
