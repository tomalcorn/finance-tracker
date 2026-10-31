import type { ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

type ListRowProps = {
  title: string;
  subtitle?: string;
  /** Shown at the end of the row, e.g. an `Amount`. */
  trailing?: ReactNode;
  onPress?: () => void;
};

/** One row of a list: a title, an optional subtitle and something at the end. Use inside `<Card list>`. */
export function ListRow({ title, subtitle, trailing, onPress }: ListRowProps) {
  const { colors } = useAppTheme();
  const content = (
    <>
      <View style={styles.text}>
        <AppText numberOfLines={1}>{title}</AppText>
        {subtitle ? (
          <AppText variant="caption" tone="muted" numberOfLines={1}>
            {subtitle}
          </AppText>
        ) : null}
      </View>
      {trailing}
    </>
  );

  if (!onPress) return <View style={styles.row}>{content}</View>;
  return (
    <Pressable
      role="button"
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && { backgroundColor: colors.surfaceMuted }]}
    >
      {content}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
  },
  text: { flex: 1, gap: 2 },
});
