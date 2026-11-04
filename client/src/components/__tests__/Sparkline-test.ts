import { sparklinePoints } from '@/components/Sparkline';

const WIDTH = 100;
const HEIGHT = 44;

describe('sparklinePoints', () => {
  it('draws a higher value above a lower one', () => {
    const [low, high] = sparklinePoints([1, 2], WIDTH, HEIGHT);

    expect(high?.y).toBeLessThan(low?.y ?? 0);
  });

  it('runs left to right in order', () => {
    const [first, second] = sparklinePoints([1, 2], WIDTH, HEIGHT);

    expect(second?.x).toBeGreaterThan(first?.x ?? 0);
  });

  it('holds a series that never moves at mid-height', () => {
    const points = sparklinePoints([5, 5, 5], WIDTH, HEIGHT);

    expect(points.map((point) => point.y)).toEqual([22, 22, 22]);
  });

  it('keeps the extremes clear of the box for the end dot', () => {
    const points = sparklinePoints([-50, 200], WIDTH, HEIGHT);

    expect(points.map((point) => point.y)).toEqual([38, 6]);
  });

  it('keeps the last point clear of the right edge for the end dot', () => {
    const points = sparklinePoints([1, 2], WIDTH, HEIGHT);

    expect(points.at(-1)?.x).toBe(94);
  });
});
