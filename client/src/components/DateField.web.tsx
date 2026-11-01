import { useId } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import type { DateFieldProps } from '@/components/DateField';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING, TYPOGRAPHY } from '@/theme/tokens';

/** react-native-web's font for text; a DOM input would otherwise take the page's serif default. */
const SYSTEM_FONT =
  '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';

/**
 * A labelled date, chosen with the browser's own date picker: react-native-web's `TextInput`
 * can't be a date input.
 */
export function DateField({ label, value, onChange, error }: DateFieldProps) {
  const { dark, colors } = useAppTheme();
  const id = useId();

  return (
    <View style={styles.field}>
      <AppText variant="label" nativeID={id}>
        {label}
      </AppText>
      <input
        type="date"
        aria-labelledby={id}
        aria-invalid={error ? true : undefined}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        style={{
          fontSize: TYPOGRAPHY.body.fontSize,
          lineHeight: `${TYPOGRAPHY.body.lineHeight}px`,
          minHeight: 44,
          boxSizing: 'border-box',
          padding: `${SPACING.sm}px ${SPACING.md}px`,
          borderRadius: RADIUS.md,
          border: `1.5px solid ${error ? colors.negative : 'transparent'}`,
          outline: 'none',
          fontFamily: SYSTEM_FONT,
          color: colors.text,
          backgroundColor: colors.surfaceMuted,
          colorScheme: dark ? 'dark' : 'light',
        }}
      />
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
