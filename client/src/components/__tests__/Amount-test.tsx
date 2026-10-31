import { render, screen } from '@testing-library/react-native';

import { Amount } from '@/components/Amount';
import { LIGHT } from '@/theme/tokens';

describe('Amount', () => {
  it('colours money out in the negative colour when signed', async () => {
    await render(<Amount value={-4.5} signed />);

    expect(screen.getByText('-£4.50')).toHaveStyle({ color: LIGHT.negative });
  });

  it('colours money in in the positive colour when signed', async () => {
    await render(<Amount value={4.5} signed />);

    expect(screen.getByText('£4.50')).toHaveStyle({ color: LIGHT.positive });
  });

  it('leaves an unsigned amount in the text colour', async () => {
    await render(<Amount value={-4.5} />);

    expect(screen.getByText('-£4.50')).toHaveStyle({ color: LIGHT.text });
  });
});
