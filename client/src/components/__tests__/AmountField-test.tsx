import { fireEvent, render, screen } from '@testing-library/react-native';
import { useState } from 'react';

import { AmountField } from '@/components/AmountField';

function Harness({ initial }: { initial: string }) {
  const [value, setValue] = useState(initial);
  return <AmountField label="Amount" value={value} onChangeText={setValue} />;
}

describe('AmountField', () => {
  it('opens the number pad', async () => {
    await render(<Harness initial="" />);

    expect(screen.getByLabelText('Amount')).toHaveProp('inputMode', 'decimal');
  });

  it('makes the amount negative with the sign button', async () => {
    await render(<Harness initial="3.40" />);

    await fireEvent.press(screen.getByRole('button', { name: 'Make negative' }));

    expect(screen.getByLabelText('Amount')).toHaveDisplayValue('-3.40');
  });

  it('makes a negative amount positive again', async () => {
    await render(<Harness initial="-3.40" />);

    await fireEvent.press(screen.getByRole('button', { name: 'Make positive' }));

    expect(screen.getByLabelText('Amount')).toHaveDisplayValue('3.40');
  });
});
