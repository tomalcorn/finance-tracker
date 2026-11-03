import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { interactiveBackground } from '@/components/interaction';
import { ProgressBar } from '@/components/ProgressBar';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

type SubscriptionRowProps = {
  name: string;
  /** Under the name, e.g. what it charges and when. */
  caption: string;
  /** At the end of the row. */
  figure: string;
  /** Its share of the total, from 0 to 1, drawn as a bar. A row with no share has no bar. */
  share?: number;
  /** Set it back, for a subscription no longer running. */
  muted?: boolean;
  onPress: () => void;
};

/** One subscription in a list: its name and figure, its share of the total, and what it charges. */
export function SubscriptionRow({
  name,
  caption,
  figure,
  share,
  muted = false,
  onPress,
}: SubscriptionRowProps) {
  const { colors } = useAppTheme();
  const tone = muted ? 'muted' : 'default';

  return (
    <Pressable
      role="button"
      aria-label={name}
      onPress={onPress}
      style={(state) => [styles.row, { backgroundColor: interactiveBackground(state, colors) }]}
    >
      <View style={styles.line}>
        <AppText tone={tone} numberOfLines={1} style={styles.name}>
          {name}
        </AppText>
        <AppText tone={tone} style={styles.figure}>
          {figure}
        </AppText>
      </View>
      {share === undefined ? null : <ProgressBar progress={share} />}
      <AppText variant="caption" tone="muted" numberOfLines={1}>
        {caption}
      </AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    gap: SPACING.xs,
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
  },
  line: { flexDirection: 'row', alignItems: 'center', gap: SPACING.md },
  name: { flex: 1 },
  figure: { fontVariant: ['tabular-nums'], fontWeight: '600' },
});
