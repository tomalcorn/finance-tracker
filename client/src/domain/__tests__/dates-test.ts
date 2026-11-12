import {
  addDays,
  addMonths,
  dateOfDay,
  dateParts,
  dayNumber,
  monthOf,
  monthWeeks,
  shiftMonths,
  startOfWeek,
  yearOf,
} from '@/domain/dates';

describe('dateParts', () => {
  it('splits a date into its year, month and day', () => {
    expect(dateParts('2026-11-12')).toEqual([2026, 11, 12]);
  });

  it('takes a month as its first day', () => {
    expect(dateParts('2026-11')).toEqual([2026, 11, 1]);
  });
});

describe('dayNumber', () => {
  it('counts the days between two dates', () => {
    expect(dayNumber('2027-01-01') - dayNumber('2026-12-25')).toBe(7);
  });

  it('turns back into the date it counted', () => {
    expect(dateOfDay(dayNumber('2028-02-29'))).toBe('2028-02-29');
  });
});

describe('addDays', () => {
  it('moves across the end of a month and a year', () => {
    expect(addDays('2026-10-31', 1)).toBe('2026-11-01');
    expect(addDays('2027-01-01', -1)).toBe('2026-12-31');
  });

  it('moves a whole day across a change of the clocks', () => {
    expect(addDays('2026-03-29', 1)).toBe('2026-03-30');
    expect(addDays('2026-10-25', -1)).toBe('2026-10-24');
  });
});

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
  it('finds the month and the year a date is in', () => {
    expect(monthOf('2026-11-12')).toBe('2026-11-01');
    expect(yearOf('2026-11-12')).toBe(2026);
  });

  it('steps months from any day of a month', () => {
    expect(addMonths('2026-11-20', -1)).toBe('2026-10-01');
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
