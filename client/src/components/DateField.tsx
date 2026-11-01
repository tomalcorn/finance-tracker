import { TextField } from '@/components/TextField';

export type DateFieldProps = {
  label: string;
  /** `YYYY-MM-DD`. */
  value: string;
  onChange: (value: string) => void;
  /** Shown under the field, which is then outlined in the negative colour. */
  error?: string;
};

/** A labelled date, typed as `YYYY-MM-DD`. The web build swaps in the browser's date picker. */
export function DateField({ label, value, onChange, error }: DateFieldProps) {
  return (
    <TextField
      label={label}
      value={value}
      onChangeText={onChange}
      placeholder="YYYY-MM-DD"
      inputMode="numeric"
      error={error}
    />
  );
}
