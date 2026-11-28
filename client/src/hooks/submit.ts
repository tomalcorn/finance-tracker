import { useState } from 'react';

/** The text to show for something thrown: an error's message, or the value itself. */
export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Call `action`: for a form whose buttons send different actions through one `useSubmit`. */
export function invoke(action: () => Promise<unknown>): Promise<unknown> {
  return action();
}

type SubmitOptions = {
  /**
   * A success ends the form, e.g. by closing its sheet, so `saving` stays true after one and the
   * form can't be sent again on its way out.
   */
  once?: boolean;
};

/** A form's save, as `useSubmit` runs it. */
export type Submit<Args extends unknown[]> = {
  /** Run the action. Never rejects: a failure lands in `failure`. */
  submit: (...args: Args) => Promise<void>;
  /** The action is under way, or, with `once`, has succeeded. */
  saving: boolean;
  /** Why the last run failed, until the next one starts. */
  failure: string | null;
  clearFailure: () => void;
};

/** Run a form's save, keeping track of whether it is under way and why it last failed. */
export function useSubmit<Args extends unknown[]>(
  action: (...args: Args) => Promise<unknown>,
  { once = false }: SubmitOptions = {},
): Submit<Args> {
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);

  async function submit(...args: Args) {
    setSaving(true);
    setFailure(null);
    try {
      await action(...args);
      if (!once) setSaving(false);
    } catch (error) {
      setFailure(messageOf(error));
      setSaving(false);
    }
  }

  return { submit, saving, failure, clearFailure: () => setFailure(null) };
}
