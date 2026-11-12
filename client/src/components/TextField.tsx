import { useId, type Ref } from 'react';
import { StyleSheet, TextInput, View, type TextInputProps } from 'react-native';

import { AppText } from '@/components/AppText';
import { NO_FOCUS_RING, fieldBorderColor, useFieldFocus } from '@/components/fieldFocus';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING, TYPOGRAPHY } from '@/theme/tokens';

type TextFieldProps = Omit<TextInputProps, 'style'> & {
  label: string;
  /** Shown under the field, which is then outlined in the negative colour. */
  error?: string;
  ref?: Ref<TextInput>;
};

/** A labelled text input, outlined in the accent while focused, with room for a validation message. */
export function TextField({ label, error, onFocus, onBlur, ...props }: TextFieldProps) {
  const { colors } = useAppTheme();
  const id = useId();
  const { focused, focusHandlers } = useFieldFocus({ onFocus, onBlur });

  return (
    <View style={styles.field}>
      <AppText variant="label" nativeID={id}>
        {label}
      </AppText>
      <TextInput
        aria-labelledby={id}
        aria-invalid={error ? true : undefined}
        placeholderTextColor={colors.textMuted}
        style={[
          TYPOGRAPHY.body,
          styles.input,
          NO_FOCUS_RING,
          {
            color: colors.text,
            backgroundColor: colors.surfaceMuted,
            borderColor: fieldBorderColor(colors, { error, focused }),
          },
        ]}
        {...props}
        {...focusHandlers}
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
  input: {
    minHeight: 44,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderRadius: RADIUS.md,
    borderWidth: 1.5,
  },
});
