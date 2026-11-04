import { StyleSheet, View } from 'react-native';

import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

type SparkBarsProps = {
  /** The series, oldest first. Anything below zero draws nothing. */
  values: readonly number[];
  /** Says what the bars show, for a screen reader. */
  label: string;
  height?: number;
};

const CORNER = 4;
const MAX_BAR_WIDTH = 24;

/** Small bars with no axes, the latest in the accent colour and the rest in a tint of it. */
export function SparkBars({ values, label, height = 44 }: SparkBarsProps) {
  const { colors } = useAppTheme();
  const highest = Math.max(...values, 0);
  const lastIndex = values.length - 1;

  return (
    <View accessible role="img" aria-label={label} style={[styles.bars, { height }]}>
      {values.map((value, index) => (
        <View
          key={index}
          style={[
            styles.bar,
            {
              height: highest > 0 ? (Math.max(value, 0) / highest) * height : 0,
              backgroundColor: index === lastIndex ? colors.accent : colors.accentSoft,
            },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  bars: { flexDirection: 'row', alignItems: 'flex-end', gap: SPACING.xs },
  bar: {
    flex: 1,
    maxWidth: MAX_BAR_WIDTH,
    borderTopLeftRadius: CORNER,
    borderTopRightRadius: CORNER,
  },
});
