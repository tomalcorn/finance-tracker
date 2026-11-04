import { useState } from 'react';
import { View, type LayoutChangeEvent } from 'react-native';
import Svg, { Circle, Path } from 'react-native-svg';

import { useAppTheme } from '@/theme/theme';

type SparklineProps = {
  /** The series, oldest first. */
  values: readonly number[];
  height?: number;
  /** Shade the space under the line. */
  area?: boolean;
};

type Point = { x: number; y: number };

const LINE_WIDTH = 2;
const DOT_RADIUS = 4;
const DOT_RING = 2;
const AREA_OPACITY = 0.15;
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
export function Sparkline({ values, height = 44, area = false }: SparklineProps) {
  const { colors } = useAppTheme();
  const [width, setWidth] = useState(0);
  const points = width > 0 ? sparklinePoints(values, width, height) : [];
  const start = points[0];
  const end = points.at(-1);
  const line = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x} ${point.y}`)
    .join(' ');

  function measure(event: LayoutChangeEvent) {
    setWidth(event.nativeEvent.layout.width);
  }

  return (
    <View onLayout={measure} style={{ height }}>
      {start && end ? (
        <Svg width={width} height={height}>
          {area ? (
            <Path
              d={`${line} L${end.x} ${height} L${start.x} ${height} Z`}
              fill={colors.accent}
              fillOpacity={AREA_OPACITY}
            />
          ) : null}
          <Path
            d={line}
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
