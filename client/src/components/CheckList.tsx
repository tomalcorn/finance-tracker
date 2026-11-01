import { useId } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { interactiveBackground } from '@/components/interaction';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

/** One choice in a `CheckList`. */
export type CheckOption = {
  value: string;
  label: string;
  /** Shown under the label, e.g. an amount. */
  caption?: string;
};

type CheckListProps = {
  label: string;
  options: readonly CheckOption[];
  selected: readonly string[];
  onChange: (selected: string[]) => void;
};

/** A labelled list of choices, any number of which can be ticked. */
export function CheckList({ label, options, selected, onChange }: CheckListProps) {
  const { colors } = useAppTheme();
  const id = useId();

  function toggle(value: string) {
    onChange(
      selected.includes(value) ? selected.filter((one) => one !== value) : [...selected, value],
    );
  }

  return (
    <View style={styles.field}>
      <AppText variant="label" nativeID={id}>
        {label}
      </AppText>
      <View
        role="group"
        aria-labelledby={id}
        style={[styles.box, { backgroundColor: colors.surfaceMuted }]}
      >
        {options.map((option, index) => {
          const checked = selected.includes(option.value);
          return (
            <Pressable
              key={option.value}
              role="checkbox"
              aria-checked={checked}
              aria-label={option.label}
              onPress={() => toggle(option.value)}
              style={(state) => [
                styles.option,
                index > 0 && {
                  borderTopColor: colors.border,
                  borderTopWidth: StyleSheet.hairlineWidth,
                },
                { backgroundColor: interactiveBackground(state, colors) },
              ]}
            >
              <View
                style={[
                  styles.tick,
                  checked
                    ? { backgroundColor: colors.accent, borderColor: colors.accent }
                    : { borderColor: colors.textMuted },
                ]}
              >
                {checked ? (
                  <AppText variant="caption" style={{ color: colors.onAccent }}>
                    ✓
                  </AppText>
                ) : null}
              </View>
              <View style={styles.text}>
                <AppText numberOfLines={1}>{option.label}</AppText>
                {option.caption ? (
                  <AppText variant="caption" tone="muted" numberOfLines={1}>
                    {option.caption}
                  </AppText>
                ) : null}
              </View>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: SPACING.xs },
  box: { borderRadius: RADIUS.md, overflow: 'hidden' },
  option: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
    paddingHorizontal: SPACING.md,
    paddingVertical: SPACING.sm,
  },
  tick: {
    width: 22,
    height: 22,
    borderRadius: RADIUS.sm - 2,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: { flex: 1, gap: 2 },
});
