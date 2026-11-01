import { initial } from '@/quickExpenses/QuickButtonTile';

describe('initial', () => {
  it('takes the first letter, in capitals', () => {
    expect(initial('coffee')).toBe('C');
  });

  it('skips punctuation and spaces before it', () => {
    expect(initial(' [probe] 2026')).toBe('P');
  });

  it('takes a leading digit', () => {
    expect(initial('7-Eleven')).toBe('7');
  });

  it('is empty for a name with no letters or digits', () => {
    expect(initial('…')).toBe('');
  });
});
