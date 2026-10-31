import { useId } from 'react';
import { StyleSheet, TextInput, View, type TextInputProps } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING, TYPOGRAPHY } from '@/theme/tokens';

type TextFieldProps = Omit<TextInputProps, 'style'> & {
  label: string;
  /** Shown under the field, which is then outlined in the negative colour. */
  error?: string;
};

/** A labelled text input, with room for a validation message. */
export function TextField({ label, error, ...props }: TextFieldProps) {
  const { colors } = useAppTheme();
  const id = useId();

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
          {
            color: colors.text,
            backgroundColor: colors.surfaceMuted,
            borderColor: error ? colors.negative : 'transparent',
          },
        ]}
        {...props}
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
