import { addDays, formatFieldDay, formatLongDay, relativeDayName } from '@/theme/formatDate';

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

describe('relativeDayName', () => {
  it('names today, yesterday and tomorrow', () => {
    expect(relativeDayName('2026-11-12', '2026-11-12')).toBe('Today');
    expect(relativeDayName('2026-11-11', '2026-11-12')).toBe('Yesterday');
    expect(relativeDayName('2026-11-13', '2026-11-12')).toBe('Tomorrow');
  });

  it('names nothing further away', () => {
    expect(relativeDayName('2026-11-10', '2026-11-12')).toBeNull();
  });

  it('counts back across a year', () => {
    expect(relativeDayName('2026-12-31', '2027-01-01')).toBe('Yesterday');
  });
});

describe('formatFieldDay', () => {
  it('leaves the year off a date in this year', () => {
    expect(formatFieldDay('2026-11-10', '2026-11-12')).toBe('Tue 10 Nov');
  });

  it('adds the year to a date in another', () => {
    expect(formatFieldDay('2025-11-10', '2026-11-12')).toBe('Mon 10 Nov 2025');
  });
});

describe('formatLongDay', () => {
  it('spells the date out', () => {
    const long = formatLongDay('2026-11-10');
    for (const part of ['Tuesday', '10', 'November', '2026']) expect(long).toContain(part);
  });
});
