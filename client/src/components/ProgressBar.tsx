import { StyleSheet, View } from 'react-native';

import { useAppTheme } from '@/theme/theme';
import { RADIUS } from '@/theme/tokens';

type ProgressBarProps = {
  /** How far along, from 0 to 1. Values outside that range are clamped. */
  progress: number;
  /** Draw the bar in the warning colour, e.g. for a budget nearly spent. */
  warn?: boolean;
  /**
   * A further fraction, drawn lighter after the progress: what is about to be added, e.g. a
   * pot's plan for the month.
   */
  planned?: number;
};

/** A horizontal bar filled to a fraction, e.g. a savings goal or a budget's spend. */
export function ProgressBar({ progress, warn = false, planned = 0 }: ProgressBarProps) {
  const { colors } = useAppTheme();
  const fraction = Math.min(Math.max(progress, 0), 1);
  const percent = Math.round(fraction * 100);
  const projected = Math.round(Math.min(fraction + Math.max(planned, 0), 1) * 100);
  const colour = warn ? colors.warning : colors.accent;

  return (
    <View
      accessible
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={percent}
      aria-valuetext={projected > percent ? `${percent}%, ${projected}% after plan` : undefined}
      style={[styles.track, { backgroundColor: colors.surfaceMuted }]}
    >
      {projected > percent ? (
        <View
          style={[styles.fill, styles.planned, { width: `${projected}%`, backgroundColor: colour }]}
        />
      ) : null}
      <View style={[styles.fill, { width: `${percent}%`, backgroundColor: colour }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  track: { height: 8, borderRadius: RADIUS.pill, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: RADIUS.pill },
  // Under the fill, reaching past it in a lighter shade of the same colour.
  planned: { position: 'absolute', left: 0, top: 0, opacity: 0.35 },
});
