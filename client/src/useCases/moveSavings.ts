import type { Payment } from '@/domain/entities';
import type { CategoryView, PaymentView } from '@/domain/readModels';
import { RepositoryError } from '@/ports/errors';
import type { Repository } from '@/ports/repository';
import { MoveSavingsError } from '@/useCases/errors';

/** Which way the money goes: into savings from a bank account, or back out to it. */
export type SavingsDirection = 'deposit' | 'withdraw';

/** One move of money into or out of savings, as `savingsMoveOf` makes it from the form. */
export type SavingsMove = {
  direction: SavingsDirection;
  /** How much moves, in pounds; always above zero, whichever the direction. */
  amount: number;
  bankAccountId: string;
  /** `YYYY-MM-DD`. */
  paymentDate: string;
  name: string;
};

/**
 * Move money into or out of a savings tracker: one expense booked to the tracker, paid from
 * `bankAccountId` for a deposit, and negative (money coming back to the account) for a withdrawal.
 *
 * @returns The payment written.
 * @throws {MoveSavingsError} when the payment fails its rules or could not be written.
 */
export async function moveSavings(
  payments: Repository<Payment, PaymentView>,
  savings: CategoryView,
  move: SavingsMove,
): Promise<Payment> {
  const row = {
    payment_type: 'expense',
    name: move.name,
    expense: move.direction === 'deposit' ? move.amount : -move.amount,
    payment_date: move.paymentDate,
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
