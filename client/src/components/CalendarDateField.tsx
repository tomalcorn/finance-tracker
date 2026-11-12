import { type SymbolViewProps } from 'expo-symbols';
import { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { Calendar } from '@/components/Calendar';
import type { DateFieldProps } from '@/components/DateField';
import { DateChips, DateFieldValue, spokenDate } from '@/components/dateFieldParts';
import { Field, FieldBox } from '@/components/Field';
import { NO_FOCUS_RING, useFieldFocus } from '@/components/fieldFocus';
import { focusOnWeb, scrollIntoViewOnWeb } from '@/components/webOnly';
import { today as todayDate } from '@/domain/entities';
import { isCalendarDate } from '@/theme/formatDate';
import { useAppTheme } from '@/theme/theme';

const OPEN: SymbolViewProps['name'] = { ios: 'chevron.up', web: 'expand_less' };
const CLOSED: SymbolViewProps['name'] = { ios: 'chevron.down', web: 'expand_more' };

/**
 * A labelled date, picked from the app's own calendar, which opens in place under the field like
 * `SelectField`'s list, so it works inside a `Sheet`.
 */
export function CalendarDateField({
  label,
  value,
  onChange,
  error,
  optional = false,
  quickPicks = true,
}: DateFieldProps) {
  const { colors } = useAppTheme();
  const [open, setOpen] = useState(false);
  const { focused, focusHandlers } = useFieldFocus();
  const field = useRef<View>(null);
  const calendar = useRef<View>(null);
  const today = todayDate();

  // A calendar that opens low in a sheet would otherwise have its last rows out of sight.
  useEffect(() => {
    if (open) scrollIntoViewOnWeb(calendar.current);
  }, [open]);

  /** Closes the calendar from inside it, where focus is, so focus goes back to the field. */
  function close() {
    setOpen(false);
    focusOnWeb(field.current);
  }

  return (
    <Field
      label={label}
      error={error}
      labelActions={
        <DateChips
          label={label}
          value={value}
          today={today}
          quickPicks={quickPicks}
          optional={optional}
          onChange={(date) => {
            onChange(date);
            setOpen(false);
          }}
        />
      }
    >
      <FieldBox error={error} focused={focused || open}>
        <Pressable
          ref={field}
          role="button"
          aria-label={`${label}, ${spokenDate(value, today)}`}
          aria-expanded={open}
          aria-invalid={error ? true : undefined}
          onPress={() => setOpen(!open)}
          style={NO_FOCUS_RING}
          {...focusHandlers}
        >
          <DateFieldValue value={value} today={today} trailing={open ? OPEN : CLOSED} />
        </Pressable>
        {open ? (
          <View ref={calendar} style={[styles.calendar, { borderTopColor: colors.border }]}>
            <Calendar
              value={isCalendarDate(value) ? value : null}
              today={today}
              onSelect={(date) => {
                onChange(date);
                close();
              }}
              onDismiss={close}
            />
          </View>
        ) : null}
      </FieldBox>
    </Field>
  );
}

const styles = StyleSheet.create({
  calendar: { borderTopWidth: StyleSheet.hairlineWidth },
});
