import { useId, type Ref } from 'react';
import { StyleSheet, TextInput, type TextInputProps } from 'react-native';

import { FIELD_BORDER_WIDTH, Field } from '@/components/Field';
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
    <Field label={label} labelId={id} error={error}>
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
    </Field>
  );
}

const styles = StyleSheet.create({
  input: {
    minHeight: 44,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
    borderRadius: RADIUS.md,
    borderWidth: FIELD_BORDER_WIDTH,
  },
});
