import { today, type Category, type Payment } from '@/domain/entities';
import type { CategoryView, PaymentView } from '@/domain/readModels';
import { RepositoryError } from '@/ports/errors';
import type { Repository } from '@/ports/repository';
import { BankOneOffsError, NothingToBankError } from '@/useCases/errors';

/**
 * Bank what is planned for each pot this month: one expense per pot, booked to the pot itself and
 * paid from `bankAccountId`, then each pot's plan cleared to nothing, since it is done for the
 * month. A pot's balance is its starting balance plus the payments booked to it, so the payment is
 * all the money there is to write.
 *
 * The payments are written before the plans, so a failed second write leaves the money banked
 * and only the plan still showing, which counts as nothing left to bank this month.
 *
 * @returns The payments written.
 * @throws {NothingToBankError} when a pot has nothing planned this month; nothing is written.
 * @throws {BankOneOffsError} when the payments or plans fail their rules or could not be written.
 */
export async function bankOneOffs(
  payments: Repository<Payment, PaymentView>,
  categories: Repository<Category, CategoryView>,
  pots: readonly CategoryView[],
  bankAccountId: string,
  paymentDate: string = today(),
): Promise<Payment[]> {
  const empty = pots.find((pot) => pot.budget <= 0);
  if (empty) throw new NothingToBankError(empty.name);

  const rows = pots.map((pot) => ({
    payment_type: 'expense',
    name: `Bank: ${pot.name}`,
    expense: pot.budget,
    payment_date: paymentDate,
    bank_account_id: bankAccountId,
    category_id: pot.id,
  }));
  let built: Payment[];
  let cleared: Category[];
  try {
    built = await payments.build(rows);
    cleared = await categories.build(pots.map((pot) => ({ ...pot, budget: 0 })));
    await payments.save(built);
  } catch (error) {
    if (!(error instanceof RepositoryError)) throw error;
    throw new BankOneOffsError(`Could not bank the pots: ${error.message}`, { cause: error });
  }
  try {
    await categories.save(cleared);
  } catch (error) {
    if (!(error instanceof RepositoryError)) throw error;
    throw new BankOneOffsError(
      `The pots were banked, but their plans could not be cleared: ${error.message}`,
      { cause: error },
    );
  }
  return built;
}
