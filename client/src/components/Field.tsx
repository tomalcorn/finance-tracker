import { type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { fieldBorderColor } from '@/components/fieldFocus';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

/** The width of a field's outline, drawn in a colour only for focus or an error. */
export const FIELD_BORDER_WIDTH = 1.5;

/** The least height of a row inside a `FieldBox`, so the box stands as tall as a `TextField`. */
export const FIELD_ROW_HEIGHT = 44 - 2 * FIELD_BORDER_WIDTH;

type FieldProps = {
  label: string;
  /** An id for the label, for a control that takes its name from it with `aria-labelledby`. */
  labelId?: string;
  /** Shown beside the label, e.g. a date field's quick picks. */
  labelActions?: ReactNode;
  /** Shown under the control. */
  error?: string;
  /** The control itself. */
  children: ReactNode;
};

/** A form field's frame: its label, the control, and a validation message under it. */
export function Field({ label, labelId, labelActions, error, children }: FieldProps) {
  const name = (
    <AppText variant="label" nativeID={labelId} style={labelActions ? styles.label : undefined}>
      {label}
    </AppText>
  );

  return (
    <View style={styles.field}>
      {labelActions ? (
        <View style={styles.labelRow}>
          {name}
          {labelActions}
        </View>
      ) : (
        name
      )}
      {children}
      {error ? (
        <AppText variant="caption" tone="negative">
          {error}
        </AppText>
      ) : null}
    </View>
  );
}

type FieldBoxProps = {
  /** Outlines the box in the negative colour. */
  error?: string;
  /** Outlines the box in the accent. */
  focused?: boolean;
  children: ReactNode;
};

/**
 * The box of a field that opens in place, such as a list of choices or a calendar: rounded, and
 * outlined as a `TextField` is.
 */
export function FieldBox({ error, focused = false, children }: FieldBoxProps) {
  const { colors } = useAppTheme();
  return (
    <View
      style={[
        styles.box,
        {
          backgroundColor: colors.surfaceMuted,
          borderColor: fieldBorderColor(colors, { error, focused }),
        },
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: SPACING.xs },
  labelRow: { flexDirection: 'row', alignItems: 'center', gap: SPACING.xs },
  label: { flex: 1 },
  box: { borderRadius: RADIUS.md, borderWidth: FIELD_BORDER_WIDTH, overflow: 'hidden' },
});
