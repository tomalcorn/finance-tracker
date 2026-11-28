import { fireEvent, render, screen } from '@testing-library/react-native';

import { SavingsMoveForm } from '@/budget/SavingsMoveForm';

const BANK_ACCOUNTS = [{ value: '3c4d5e6f-0000-4000-8000-000000000001', label: 'Current' }];

describe('SavingsMoveForm', () => {
  it('offers no ± button, since the direction comes from the button pressed', async () => {
    await render(
      <SavingsMoveForm
        direction="withdraw"
        bankAccounts={BANK_ACCOUNTS}
        onSubmit={() => Promise.resolve()}
        onCancel={() => {}}
      />,
    );

    expect(screen.queryByRole('button', { name: 'Make negative' })).not.toBeOnTheScreen();
  });

  it('shows why the move failed, keeping the sheet open', async () => {
    await render(
      <SavingsMoveForm
        direction="deposit"
        bankAccounts={BANK_ACCOUNTS}
        onSubmit={() => Promise.reject(new Error('Could not move the money: network down'))}
        onCancel={() => {}}
      />,
    );
    await fireEvent.changeText(screen.getByLabelText('Amount'), '50');

    await fireEvent.press(screen.getByRole('button', { name: 'Deposit £50.00' }));

    expect(await screen.findByText('Could not move the money: network down')).toBeOnTheScreen();
  });

  it('lets a failed move be tried again', async () => {
    await render(
      <SavingsMoveForm
        direction="deposit"
        bankAccounts={BANK_ACCOUNTS}
        onSubmit={() => Promise.reject(new Error('network down'))}
        onCancel={() => {}}
      />,
    );
    await fireEvent.changeText(screen.getByLabelText('Amount'), '50');
    await fireEvent.press(screen.getByRole('button', { name: 'Deposit £50.00' }));
    await screen.findByText('network down');

    expect(screen.getByRole('button', { name: 'Deposit £50.00' })).toBeEnabled();
  });
});
