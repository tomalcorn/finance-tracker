import { useRef, useState } from 'react';

import type { PaymentView } from '@/domain/readModels';

type OptimisticChecks = {
  /** The payments as they should look, with each tick still being saved already applied. */
  applyTo: (payments: readonly PaymentView[]) => PaymentView[];
  /** Flip a payment's tick at once, and save it behind the scenes. */
  toggle: (payment: PaymentView) => Promise<void>;
};

/**
 * Ticks that show as soon as they are tapped, rather than once saved and read back. Taps on a
 * payment still being saved wait their turn, so the last one is what ends up stored. A tick that
 * can't be saved goes back to what is stored.
 *
 * Args:
 *   save: Store a payment's tick. It settles once the fresh rows have been read back, so nothing
 *     flickers when the tick being shown gives way to the stored one.
 *   onFailure: Called with the payment and the error when a tick can't be saved.
 */
export function useOptimisticChecks(
  save: (payment: PaymentView, checked: boolean) => Promise<void>,
  onFailure: (payment: PaymentView, error: unknown) => void,
): OptimisticChecks {
  const [shown, setShown] = useState<ReadonlyMap<string, boolean>>(() => new Map());
  const wanted = useRef(new Map<string, boolean>());
  const saving = useRef(new Set<string>());

  function applyTo(payments: readonly PaymentView[]): PaymentView[] {
    return payments.map((payment) => {
      const checked = shown.get(payment.id);
      return checked === undefined ? payment : { ...payment, checked };
    });
  }

  async function toggle(payment: PaymentView) {
    wanted.current.set(payment.id, !payment.checked);
    setShown(new Map(wanted.current));
    if (saving.current.has(payment.id)) return;

    saving.current.add(payment.id);
    try {
      let saved: boolean | undefined;
      while (saved !== wanted.current.get(payment.id)) {
        saved = wanted.current.get(payment.id) ?? !payment.checked;
        await save(payment, saved);
      }
    } catch (error) {
      onFailure(payment, error);
    } finally {
      saving.current.delete(payment.id);
      wanted.current.delete(payment.id);
      setShown(new Map(wanted.current));
    }
  }

  return { applyTo, toggle };
}
