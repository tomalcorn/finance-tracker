import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

/** What each part of the bar is, shown when the pointer is over it, e.g. "Spent £64.00". */
export type ProgressBarLabels = {
  /** The filled part. */
  progress?: string;
  /** The lighter part after it, when there is one. */
  planned?: string;
  /** The empty part at the end. */
  rest?: string;
};

type Segment = keyof ProgressBarLabels;

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
  /** What each part is, shown on hover. A part with no label shows nothing. */
  labels?: ProgressBarLabels;
};

/** A horizontal bar filled to a fraction, e.g. a savings goal or a budget's spend. */
export function ProgressBar({ progress, warn = false, planned = 0, labels }: ProgressBarProps) {
  const { colors } = useAppTheme();
  const [hovered, setHovered] = useState<Segment | null>(null);
  const fraction = Math.min(Math.max(progress, 0), 1);
  const percent = Math.round(fraction * 100);
  const projected = Math.round(Math.min(fraction + Math.max(planned, 0), 1) * 100);
  const colour = warn ? colors.warning : colors.accent;

  // Each labelled part, by where it starts and ends along the bar, in percent.
  const segments = (
    [
      ['progress', 0, percent],
      ['planned', percent, projected],
      ['rest', projected, 100],
    ] as const
  ).filter(([segment, start, end]) => labels?.[segment] && end > start);
  const shown = segments.find(([segment]) => segment === hovered);

  return (
    <View style={styles.frame}>
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
            style={[
              styles.fill,
              styles.planned,
              { width: `${projected}%`, backgroundColor: colour },
            ]}
          />
        ) : null}
        <View style={[styles.fill, { width: `${percent}%`, backgroundColor: colour }]} />
      </View>
      {segments.map(([segment, start, end]) => (
        <View
          key={segment}
          aria-hidden
          testID={`progress-${segment}`}
          onPointerEnter={() => setHovered(segment)}
          onPointerLeave={() => setHovered((current) => (current === segment ? null : current))}
          style={[styles.zone, { left: `${start}%`, width: `${end - start}%` }]}
        />
      ))}
      {shown ? (
        <View
          pointerEvents="none"
          style={[
            styles.tip,
            { backgroundColor: colors.text },
            // Anchored at the part's start, or its end when it starts past the middle, so the
            // label stays over the bar.
            shown[1] <= 50 ? { left: `${shown[1]}%` } : { right: `${100 - shown[2]}%` },
          ]}
        >
          <AppText variant="caption" numberOfLines={1} style={{ color: colors.background }}>
            {labels?.[shown[0]]}
          </AppText>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  frame: { position: 'relative', zIndex: 1 },
  track: { height: 8, borderRadius: RADIUS.pill, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: RADIUS.pill },
  // Under the fill, reaching past it in a lighter shade of the same colour.
  planned: { position: 'absolute', left: 0, top: 0, opacity: 0.35 },
  // Taller than the bar, so it is easy to land the pointer on.
  zone: { position: 'absolute', top: -SPACING.sm, bottom: -SPACING.sm },
  tip: {
    position: 'absolute',
    bottom: 8 + SPACING.xs,
    paddingHorizontal: SPACING.sm,
    paddingVertical: 2,
    borderRadius: RADIUS.sm,
  },
});
