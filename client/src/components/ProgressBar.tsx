import { StyleSheet, View } from 'react-native';

import { useAppTheme } from '@/theme/theme';
import { RADIUS } from '@/theme/tokens';

type ProgressBarProps = {
  /** How far along, from 0 to 1. Values outside that range are clamped. */
  progress: number;
  /** Draw the bar in the warning colour, e.g. for a budget nearly spent. */
  warn?: boolean;
};

/** A horizontal bar filled to a fraction, e.g. a savings goal or a budget's spend. */
export function ProgressBar({ progress, warn = false }: ProgressBarProps) {
  const { colors } = useAppTheme();
  const percent = Math.round(Math.min(Math.max(progress, 0), 1) * 100);

  return (
    <View
      accessible
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      style={[styles.track, { backgroundColor: colors.surfaceMuted }]}
    >
      <View
        style={[
          styles.fill,
          { width: `${percent}%`, backgroundColor: warn ? colors.warning : colors.accent },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  track: { height: 8, borderRadius: RADIUS.pill, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: RADIUS.pill },
});
