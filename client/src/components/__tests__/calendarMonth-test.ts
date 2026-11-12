import {
  addMonths,
  monthOf,
  monthWeeks,
  shiftMonths,
  startOfWeek,
} from '@/components/calendarMonth';

describe('monthWeeks', () => {
  it('lays a month out in weeks from Monday', () => {
    // 1 November 2026 is a Sunday.
    const weeks = monthWeeks('2026-11-01');

    expect(weeks[0]).toEqual([null, null, null, null, null, null, '2026-11-01']);
    expect(weeks[1]?.[0]).toBe('2026-11-02');
    expect(weeks.at(-1)).toEqual(['2026-11-30', null, null, null, null, null, null]);
    expect(weeks).toHaveLength(6);
  });

  it('holds every day of the month once', () => {
    const days = monthWeeks('2028-02-01')
      .flat()
      .filter((day) => day !== null);

    expect(days).toHaveLength(29);
    expect(days[0]).toBe('2028-02-01');
    expect(days.at(-1)).toBe('2028-02-29');
  });

  it('needs only four weeks for a February that starts on a Monday', () => {
    expect(monthWeeks('2027-02-01')).toHaveLength(4);
  });
});

describe('month arithmetic', () => {
  it('finds the month a date is in', () => {
    expect(monthOf('2026-11-12')).toBe('2026-11-01');
  });

  it('steps months across a year', () => {
    expect(addMonths('2026-12-01', 1)).toBe('2027-01-01');
    expect(addMonths('2026-01-01', -1)).toBe('2025-12-01');
  });

  it('keeps the day when shifting months, or takes the shorter month’s last', () => {
    expect(shiftMonths('2026-11-12', 1)).toBe('2026-12-12');
    expect(shiftMonths('2026-01-31', 1)).toBe('2026-02-28');
    expect(shiftMonths('2028-02-29', -12)).toBe('2027-02-28');
  });

  it('finds the Monday a week starts on', () => {
    expect(startOfWeek('2026-11-12')).toBe('2026-11-09');
    expect(startOfWeek('2026-11-09')).toBe('2026-11-09');
    expect(startOfWeek('2026-11-01')).toBe('2026-10-26');
  });
});
