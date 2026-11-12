export type DateFieldProps = {
  label: string;
  /** `YYYY-MM-DD`, or empty for no date. */
  value: string;
  onChange: (value: string) => void;
  /** Shown under the field, which is then outlined in the negative colour. */
  error?: string;
  /** Whether the date may be left empty, which adds a Clear chip while one is set. */
  optional?: boolean;
  /** Offer Today and Yesterday as one-tap choices beside the label. On by default. */
  quickPicks?: boolean;
};

/**
 * A labelled date, picked from the app's calendar. The web build keeps the phone's own date picker
 * on touch screens, where it beats ours, and uses the calendar with a mouse or trackpad.
 */
export { CalendarDateField as DateField } from '@/components/CalendarDateField';
