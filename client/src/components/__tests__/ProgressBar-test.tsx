import { render, screen } from '@testing-library/react-native';

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
});
