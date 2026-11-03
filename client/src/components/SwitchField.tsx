import { StyleSheet, Switch, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

type SwitchFieldProps = {
  label: string;
  /** Under the label, saying what turning it on means. */
  caption?: string;
  value: boolean;
  onChange: (value: boolean) => void;
};

/** A labelled on/off choice. */
export function SwitchField({ label, caption, value, onChange }: SwitchFieldProps) {
  const { colors } = useAppTheme();

  return (
    <View style={styles.row}>
      <View style={styles.text}>
        <AppText variant="label">{label}</AppText>
        {caption ? (
          <AppText variant="caption" tone="muted">
            {caption}
          </AppText>
        ) : null}
      </View>
      <Switch
        aria-label={label}
        value={value}
        onValueChange={onChange}
        trackColor={{ true: colors.accent, false: colors.surfaceMuted }}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: SPACING.md },
  text: { flex: 1, gap: 2 },
});
