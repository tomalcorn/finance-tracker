import { today, type Payment } from '@/domain/entities';
import type { CategoryView, PaymentView } from '@/domain/readModels';
import { RepositoryError } from '@/ports/errors';
import type { Repository } from '@/ports/repository';
import { MoveSavingsError, NonPositiveSavingsAmountError } from '@/useCases/errors';

/** Which way the money goes: into savings from a bank account, or back out to it. */
export type SavingsDirection = 'deposit' | 'withdraw';

/** One move of money into or out of savings. */
export type SavingsMove = {
  direction: SavingsDirection;
  /** How much moves, in pounds; always above zero, whichever the direction. */
  amount: number;
  bankAccountId: string;
  /** `YYYY-MM-DD`; today when left out. */
  paymentDate?: string;
  /** The payment's name; a default for the direction when left out or blank. */
  name?: string;
};

const DEFAULT_NAMES: Record<SavingsDirection, string> = {
  deposit: 'Savings deposit',
  withdraw: 'Savings withdrawal',
};

/**
 * Move money into or out of a savings tracker: one expense booked to the tracker, paid from
 * `bankAccountId` for a deposit, and negative (money coming back to the account) for a withdrawal.
 *
 * @returns The payment written.
 * @throws {NonPositiveSavingsAmountError} when the amount isn't above zero; nothing is written.
 * @throws {MoveSavingsError} when the payment fails its rules or could not be written.
 */
export async function moveSavings(
  payments: Repository<Payment, PaymentView>,
  savings: CategoryView,
  move: SavingsMove,
): Promise<Payment> {
  if (!(move.amount > 0)) throw new NonPositiveSavingsAmountError(move.amount);

  const row = {
    payment_type: 'expense',
    name: move.name?.trim() || DEFAULT_NAMES[move.direction],
    expense: move.direction === 'deposit' ? move.amount : -move.amount,
    payment_date: move.paymentDate ?? today(),
    bank_account_id: move.bankAccountId,
    category_id: savings.id,
  };
  try {
    const [built] = await payments.build([row]);
    if (!built) throw new MoveSavingsError('Could not build the savings payment.');
    await payments.save([built]);
    return built;
  } catch (error) {
    if (!(error instanceof RepositoryError)) throw error;
    throw new MoveSavingsError(`Could not move the money: ${error.message}`, { cause: error });
  }
}
