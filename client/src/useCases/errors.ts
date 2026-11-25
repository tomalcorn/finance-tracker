/** Base class for errors raised by a use case. */
export class UseCaseError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = new.target.name;
  }
}

/** A quick button could not log its payment. */
export class QuickPaymentError extends UseCaseError {}

/** A tap left a field the payment needs neither preset on the button nor filled in. */
export class IncompleteQuickPaymentError extends QuickPaymentError {
  readonly buttonName: string;
  readonly missing: readonly string[];

  constructor(buttonName: string, missing: readonly string[]) {
    super(`Quick button "${buttonName}" cannot log a payment without ${missing.join(', ')}.`);
    this.buttonName = buttonName;
    this.missing = missing;
  }
}

/** The payment failed its rules, or could not be written. */
export class QuickPaymentWriteError extends QuickPaymentError {}

/** Pots could not be banked. */
export class BankOneOffsError extends UseCaseError {}

/** A pot was asked to be banked with nothing planned for it this month. */
export class NothingToBankError extends BankOneOffsError {
  readonly potName: string;

  constructor(potName: string) {
    super(`"${potName}" has nothing planned to bank this month.`);
    this.potName = potName;
  }
}

/** Money could not be moved into or out of savings. */
export class MoveSavingsError extends UseCaseError {}

/** A deposit or withdrawal was asked for with an amount that isn't above zero. */
export class NonPositiveSavingsAmountError extends MoveSavingsError {
  readonly amount: number;

  constructor(amount: number) {
    super(`An amount to move must be above zero, not ${amount}.`);
    this.amount = amount;
  }
}
