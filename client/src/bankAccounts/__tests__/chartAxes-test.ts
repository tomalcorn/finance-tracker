import { dateTicks, formatValueTick, nearestIndex, valueTicks } from '@/bankAccounts/chartAxes';

describe('valueTicks', () => {
  it('uses round numbers', () => {
    expect(valueTicks([120, 2890])).toEqual([0, 1000, 2000, 3000]);
  });

  it('spans a series below zero', () => {
    expect(valueTicks([-812, -40])).toEqual([-1000, -500, 0]);
  });

  it('labels a top tick of zero without a sign', () => {
    expect(formatValueTick(valueTicks([-500, -100]).at(-1) ?? 1)).toBe('£0');
  });

  it('marks zero for a series crossing it', () => {
    expect(valueTicks([-300, 700])).toContain(0);
  });

  it('measures a flat series from zero', () => {
    expect(valueTicks([500, 500])).toEqual([0, 200, 400, 600]);
  });

  it('measures a flat negative series from zero', () => {
    expect(valueTicks([-500, -500])).toEqual([-600, -400, -200, 0]);
  });

  it('gives a series flat at zero an axis', () => {
    expect(valueTicks([0, 0])).toEqual([0, 50, 100]);
  });

  it('keeps ticks to the penny for a small range', () => {
    expect(valueTicks([0.1, 0.3])).toEqual([0.1, 0.2, 0.3]);
  });
});

describe('formatValueTick', () => {
  it('writes an amount in full under £10,000', () => {
    expect(formatValueTick(2500)).toBe('£2,500');
  });

  it('compacts an amount from £10,000', () => {
    expect(formatValueTick(12500)).toBe('£12.5K');
  });

  it('keeps the sign when compacting', () => {
    expect(formatValueTick(-20000)).toBe('-£20K');
  });
});

describe('dateTicks', () => {
  it('labels the first of each month', () => {
    const dates = ['2026-09-30', '2026-10-01', '2026-10-02', '2026-11-01', '2026-11-02'];

    expect(dateTicks(dates)).toEqual([
      { index: 1, label: 'Oct' },
      { index: 3, label: 'Nov' },
    ]);
  });

  it('labels both ends of a span reaching one month start', () => {
    expect(dateTicks(['2026-10-31', '2026-11-01', '2026-11-02'])).toEqual([
      { index: 0, label: '31 Oct' },
      { index: 2, label: '2 Nov' },
    ]);
  });
});

describe('nearestIndex', () => {
  it('snaps to the closest position', () => {
    expect(nearestIndex(26, 100, 5)).toBe(1);
  });

  it('stops at the start', () => {
    expect(nearestIndex(-10, 100, 5)).toBe(0);
  });

  it('stops at the end', () => {
    expect(nearestIndex(120, 100, 5)).toBe(4);
  });
});
