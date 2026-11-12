import { useId, useSyncExternalStore } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { CalendarDateField } from '@/components/CalendarDateField';
import type { DateFieldProps } from '@/components/DateField';
import { DateFieldHeader, DateFieldValue, fieldBox } from '@/components/dateFieldParts';
import { fieldBorderColor, useFieldFocus } from '@/components/fieldFocus';
import { today as todayDate } from '@/domain/entities';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

const COARSE_POINTER = '(pointer: coarse)';

function subscribe(onChange: () => void): () => void {
  const query = window.matchMedia(COARSE_POINTER);
  query.addEventListener('change', onChange);
  return () => query.removeEventListener('change', onChange);
}

/** Whether the main pointer is a finger, i.e. a phone or tablet. False in the pre-rendered page. */
function useTouchScreen(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => window.matchMedia(COARSE_POINTER).matches,
    () => false,
  );
}

/**
 * A labelled date. On a touch screen it opens the phone's own picker (iOS's wheel and calendar are
 * better on a phone than anything we'd draw); with a mouse or trackpad it opens the app's calendar,
 * in place of the browser's small one.
 */
export function DateField(props: DateFieldProps) {
  const touchScreen = useTouchScreen();
  return touchScreen ? <TouchDateField {...props} /> : <CalendarDateField {...props} />;
}

/**
 * The field drawn like the app's others, with the browser's date input laid invisibly over it, so
 * a tap opens the phone's picker. react-native-web's `TextInput` can't be a date input.
 */
function TouchDateField({
  label,
  value,
  onChange,
  error,
  optional = false,
  quickPicks = true,
}: DateFieldProps) {
  const { dark, colors } = useAppTheme();
  const labelId = useId();
  const { focused, focusHandlers } = useFieldFocus();
  const today = todayDate();

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
            borderColor: fieldBorderColor(colors, { error, focused }),
          },
        ]}
      >
        <View aria-hidden>
          <DateFieldValue value={value} today={today} />
        </View>
        <input
          type="date"
          aria-labelledby={labelId}
          aria-invalid={error ? true : undefined}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          {...focusHandlers}
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            height: '100%',
            margin: 0,
            padding: 0,
            border: 'none',
            opacity: 0,
            // Under 16px, iOS zooms the page into a focused input.
            fontSize: 16,
            cursor: 'pointer',
            colorScheme: dark ? 'dark' : 'light',
          }}
        />
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
});
