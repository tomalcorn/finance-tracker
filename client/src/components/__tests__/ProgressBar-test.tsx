import { fireEvent, render, screen } from '@testing-library/react-native';

import { ProgressBar } from '@/components/ProgressBar';

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

  it('shows what a part of the bar is while the pointer is over it', async () => {
    await render(
      <ProgressBar
        progress={0.4}
        planned={0.2}
        labels={{ progress: 'Saved £40.00', planned: 'To bank £20.00', rest: 'To go £40.00' }}
      />,
    );
    expect(screen.queryByText('To bank £20.00')).toBeNull();

    await fireEvent(
      screen.getByTestId('progress-planned', { includeHiddenElements: true }),
      'pointerEnter',
    );
    expect(screen.getByText('To bank £20.00')).toBeTruthy();

    await fireEvent(
      screen.getByTestId('progress-planned', { includeHiddenElements: true }),
      'pointerLeave',
    );
    expect(screen.queryByText('To bank £20.00')).toBeNull();
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
