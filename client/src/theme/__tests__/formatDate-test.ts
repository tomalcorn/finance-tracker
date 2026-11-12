import { formatFieldDay, formatLongDay, relativeDayName } from '@/theme/formatDate';

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
