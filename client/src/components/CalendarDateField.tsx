import { type SymbolViewProps } from 'expo-symbols';
import { useId, useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { Calendar } from '@/components/Calendar';
import type { DateFieldProps } from '@/components/DateField';
import { DateFieldHeader, DateFieldValue, fieldBox, spokenDate } from '@/components/dateFieldParts';
import { NO_FOCUS_RING, fieldBorderColor, useFieldFocus } from '@/components/fieldFocus';
import { today as todayDate } from '@/domain/entities';
import { isCalendarDate } from '@/theme/formatDate';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

const OPEN: SymbolViewProps['name'] = { ios: 'chevron.up', web: 'expand_less' };
const CLOSED: SymbolViewProps['name'] = { ios: 'chevron.down', web: 'expand_more' };

/** A `Pressable` that can be focused from code, which only the web's can. */
type Focusable = View & { focus?: () => void };

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
  const labelId = useId();
  const [open, setOpen] = useState(false);
  const { focused, focusHandlers } = useFieldFocus();
  const field = useRef<Focusable>(null);
  const today = todayDate();

  function close() {
    setOpen(false);
    if (Platform.OS === 'web') field.current?.focus?.();
  }

  return (
    <View style={styles.field}>
      <DateFieldHeader
        label={label}
        labelId={labelId}
        value={value}
        onChange={onChange}
        optional={optional}
        today={today}
        quickPicks={quickPicks}
      />
      <View
        style={[
          fieldBox,
          {
            backgroundColor: colors.surfaceMuted,
            borderColor: fieldBorderColor(colors, { error, focused: focused || open }),
          },
        ]}
      >
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
          <View style={[styles.calendar, { borderTopColor: colors.border }]}>
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
      </View>
      {error ? (
        <AppText variant="caption" tone="negative">
          {error}
        </AppText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: SPACING.xs },
  calendar: { borderTopWidth: StyleSheet.hairlineWidth },
});
