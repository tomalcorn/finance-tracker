import { today, type Payment } from '@/domain/entities';
import type { CategoryView, PaymentView } from '@/domain/readModels';
import { RepositoryError } from '@/ports/errors';
import type { Repository } from '@/ports/repository';
import { BankOneOffsError, NothingToBankError } from '@/useCases/errors';

/**
 * Bank what is planned for each pot this month: one expense per pot, booked to the pot itself and
 * paid from `bankAccountId`. A pot's balance is its starting balance plus the payments booked to
 * it, so the payment is all there is to write.
 *
 * @returns The payments written.
 * @throws {NothingToBankError} when a pot has nothing planned this month; nothing is written.
 * @throws {BankOneOffsError} when the payments fail their rules or could not be written.
 */
export async function bankOneOffs(
  payments: Repository<Payment, PaymentView>,
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
  try {
    const built = await payments.build(rows);
    await payments.save(built);
    return built;
  } catch (error) {
    if (!(error instanceof RepositoryError)) throw error;
    throw new BankOneOffsError(`Could not bank the pots: ${error.message}`, { cause: error });
  }
}
