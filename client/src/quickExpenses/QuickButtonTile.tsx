import { ActivityIndicator, Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import type { QuickButtonView } from '@/domain/readModels';
import { useAppTheme } from '@/theme/theme';
import { formatAmount } from '@/theme/formatAmount';
import { RADIUS, SPACING } from '@/theme/tokens';

type QuickButtonTileProps = {
  button: QuickButtonView;
  /** Tapping opens the button's settings instead of logging. */
  editing: boolean;
  /** Logging is under way, so the tile shows a spinner and ignores taps. */
  busy: boolean;
  onPress: () => void;
  onLongPress: () => void;
};

/** What a tap on the button will log: its amount, or that it asks first. */
function detail(button: QuickButtonView): string {
  if (button.mode === 'prompt') {
    return button.expense === null ? 'Asks for details' : `${formatAmount(button.expense)} · asks`;
  }
  return formatAmount(button.expense ?? 0);
}

/** One quick button: a large tap target that logs its payment, or opens its settings to edit. */
export function QuickButtonTile({
  button,
  editing,
  busy,
  onPress,
  onLongPress,
}: QuickButtonTileProps) {
  const { colors } = useAppTheme();

  return (
    <Pressable
      role="button"
      aria-label={editing ? `Edit ${button.name}` : button.name}
      aria-busy={busy}
      disabled={busy}
      onPress={onPress}
      onLongPress={onLongPress}
      style={({ pressed }) => [
        styles.tile,
        {
          backgroundColor: pressed ? colors.surfaceMuted : colors.surface,
          borderColor: editing ? colors.accent : colors.border,
        },
        editing && styles.editing,
        pressed && styles.pressed,
      ]}
    >
      <View style={styles.top}>
        <AppText style={styles.icon}>{button.icon ?? ''}</AppText>
        {editing ? (
          <AppText variant="caption" tone="accent">
            Edit
          </AppText>
        ) : null}
      </View>
      <AppText variant="label" numberOfLines={2}>
        {button.name}
      </AppText>
      {busy ? (
        <ActivityIndicator color={colors.accent} style={styles.spinner} />
      ) : (
        <AppText variant="caption" tone="muted" numberOfLines={1} style={styles.amount}>
          {detail(button)}
        </AppText>
      )}
    </Pressable>
  );
}

/** A dashed tile at the end of the grid, for adding a button. */
export function NewButtonTile({ onPress }: { onPress: () => void }) {
  const { colors } = useAppTheme();

  return (
    <Pressable
      role="button"
      aria-label="New button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.tile,
        styles.newTile,
        { borderColor: colors.accent },
        pressed && { backgroundColor: colors.accentSoft },
      ]}
    >
      <AppText variant="heading" tone="accent">
        +
      </AppText>
      <AppText variant="label" tone="accent">
        New button
      </AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    minHeight: 104,
    padding: SPACING.md,
    gap: SPACING.xs,
    borderRadius: RADIUS.lg,
    borderWidth: StyleSheet.hairlineWidth,
  },
  editing: { borderWidth: 1.5 },
  pressed: { transform: [{ scale: 0.97 }] },
  top: { flexDirection: 'row', justifyContent: 'space-between', minHeight: 26 },
  icon: { fontSize: 22, lineHeight: 26 },
  amount: { fontVariant: ['tabular-nums'] },
  spinner: { alignSelf: 'flex-start' },
  newTile: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderStyle: 'dashed',
  },
});
