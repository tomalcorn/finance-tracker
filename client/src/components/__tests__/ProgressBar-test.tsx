import { act, fireEvent, render, screen } from '@testing-library/react-native';

import { HOVER_DELAY_MS, ProgressBar } from '@/components/ProgressBar';

describe('ProgressBar', () => {
  it('reports its progress as a percentage', async () => {
    await render(<ProgressBar progress={0.534} />);

    expect(screen.getByRole('progressbar')).toHaveProp('aria-valuenow', 53);
  });

  it('clamps progress past the end to full', async () => {
    await render(<ProgressBar progress={1.4} />);

    expect(screen.getByRole('progressbar')).toHaveProp('aria-valuenow', 100);
  });

  it('clamps negative progress to empty', async () => {
    await render(<ProgressBar progress={-0.2} />);

    expect(screen.getByRole('progressbar')).toHaveProp('aria-valuenow', 0);
  });

  it('reports where a planned amount would take it', async () => {
    await render(<ProgressBar progress={0.4} planned={0.25} />);

    expect(screen.getByRole('progressbar')).toHaveProp('aria-valuetext', '40%, 65% after plan');
  });

  it('stops a planned amount at full', async () => {
    await render(<ProgressBar progress={0.9} planned={0.5} />);

    expect(screen.getByRole('progressbar')).toHaveProp('aria-valuetext', '90%, 100% after plan');
  });

  describe('on hover', () => {
    beforeEach(() => jest.useFakeTimers());
    afterEach(() => jest.useRealTimers());

    const labels = { progress: 'Saved £40.00', planned: 'To bank £20.00', rest: 'To go £40.00' };
    const zone = (segment: string) =>
      screen.getByTestId(`progress-${segment}`, { includeHiddenElements: true });

    it('shows what a part of the bar is once the pointer rests on it, until it leaves', async () => {
      await render(<ProgressBar progress={0.4} planned={0.2} labels={labels} />);

      await fireEvent(zone('planned'), 'pointerEnter');
      await act(() => jest.advanceTimersByTime(HOVER_DELAY_MS - 1));
      expect(screen.queryByText('To bank £20.00')).toBeNull();

      await act(() => jest.advanceTimersByTime(1));
      expect(screen.getByText('To bank £20.00')).toBeTruthy();

      await fireEvent(zone('planned'), 'pointerLeave');
      expect(screen.queryByText('To bank £20.00')).toBeNull();
    });

    it('shows nothing when the pointer only passes over', async () => {
      await render(<ProgressBar progress={0.4} planned={0.2} labels={labels} />);

      await fireEvent(zone('progress'), 'pointerEnter');
      await act(() => jest.advanceTimersByTime(HOVER_DELAY_MS / 2));
      await fireEvent(zone('progress'), 'pointerLeave');
      await act(() => jest.advanceTimersByTime(HOVER_DELAY_MS));

      expect(screen.queryByText('Saved £40.00')).toBeNull();
    });
  });

  it('has nothing to hover over for an empty part, or one with no label', async () => {
    await render(
      <ProgressBar progress={1} labels={{ progress: 'Spent £10.00', rest: 'Left £0.00' }} />,
    );

    expect(screen.getByTestId('progress-progress', { includeHiddenElements: true })).toBeTruthy();
    expect(screen.queryByTestId('progress-rest', { includeHiddenElements: true })).toBeNull();
    expect(screen.queryByTestId('progress-planned', { includeHiddenElements: true })).toBeNull();
  });
});
