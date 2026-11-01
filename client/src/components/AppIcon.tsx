import { useId } from 'react';
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from 'react-native-svg';

import { PWA } from '@/pwa';

type AppIconProps = {
  /** The icon's width and height. */
  size: number;
};

/** The ratio of an iOS app icon's corner radius to its width. */
const CORNER_RATIO = 0.225;

/**
 * The app icon, as an iOS-style rounded square: the same rising chart the home-screen icons are
 * generated from (`scripts/generate-pwa-assets.mjs`), drawn from the same `src/pwa.json` settings.
 */
export function AppIcon({ size }: AppIconProps) {
  // Several icons can share a page, so each needs its own gradient id; React's ids hold characters a
  // `url(#…)` reference can't.
  const fadeId = `app-icon-fade-${useId().replace(/[^\w-]/g, '')}`;
  const { color, chart, floor, lineWidth, dotRadius, fillOpacity } = PWA.mark;
  const points = chart.map(([x, y]) => `${x} ${y}`).join(' L');
  const [start, end] = [chart[0], chart.at(-1)];
  if (!start || !end) return null;
  const [firstX] = start;
  const [lastX, lastY] = end;

  return (
    <Svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label="Finance Tracker">
      <Defs>
        <LinearGradient id={fadeId} x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor={color} stopOpacity={fillOpacity} />
          <Stop offset="1" stopColor={color} stopOpacity={0} />
        </LinearGradient>
      </Defs>
      <Rect width={100} height={100} rx={100 * CORNER_RATIO} fill={PWA.backgroundColor} />
      <Path d={`M${points} V${floor} H${firstX} Z`} fill={`url(#${fadeId})`} />
      <Path
        d={`M${points}`}
        fill="none"
        stroke={color}
        strokeWidth={lineWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Circle cx={lastX} cy={lastY} r={dotRadius} fill={color} />
    </Svg>
  );
}
