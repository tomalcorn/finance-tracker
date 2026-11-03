import { useState } from 'react';
import { View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

import { useAppTheme } from '@/theme/theme';

type SparklineProps = {
  /** The series, oldest first. */
  values: readonly number[];
  height?: number;
};

type Point = { x: number; y: number };

const LINE_WIDTH = 2;
const DOT_RADIUS = 4;
const DOT_RING = 2;
/** Room around the plot for the end dot and its ring. */
const INSET = DOT_RADIUS + DOT_RING;

/**
 * Place a series in a box, spread evenly across it and scaled to its own lowest and highest values.
 * A series that never moves sits at mid-height.
 */
export function sparklinePoints(values: readonly number[], width: number, height: number): Point[] {
  const low = Math.min(...values);
  const range = Math.max(...values) - low;
  const plotWidth = width - INSET - LINE_WIDTH / 2;
  const plotHeight = height - INSET * 2;
  const lastIndex = Math.max(values.length - 1, 1);

  return values.map((value, index) => ({
    x: LINE_WIDTH / 2 + (index / lastIndex) * plotWidth,
    y: range === 0 ? height / 2 : INSET + (1 - (value - low) / range) * plotHeight,
  }));
}

/** A small line with no axes for how a value has moved, ending on a dot at the latest value. */
export function Sparkline({ values, height = 44 }: SparklineProps) {
  const { colors } = useAppTheme();
  const [width, setWidth] = useState(0);
  const points = width > 0 ? sparklinePoints(values, width, height) : [];
  const end = points.at(-1);

  function measure(event: LayoutChangeEvent) {
    setWidth(event.nativeEvent.layout.width);
  }

  return (
    <View onLayout={measure} style={{ height }}>
      {end ? (
        <Svg width={width} height={height}>
          <Path
            d={points
              .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x} ${point.y}`)
              .join(' ')}
            fill="none"
            stroke={colors.accent}
            strokeWidth={LINE_WIDTH}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          <Circle
            cx={end.x}
            cy={end.y}
            r={DOT_RADIUS}
            fill={colors.accent}
            stroke={colors.surface}
            strokeWidth={DOT_RING}
          />
        </Svg>
      ) : null}
    </View>
  );
}
