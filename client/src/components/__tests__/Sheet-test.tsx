import { fireEvent, render, screen } from '@testing-library/react-native';
import type { ReactElement } from 'react';
import { Text } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { Sheet } from '@/components/Sheet';

/** An iPhone-sized window, with the notch and home indicator insets. */
const METRICS = {
  frame: { x: 0, y: 0, width: 390, height: 844 },
  insets: { top: 47, left: 0, right: 0, bottom: 34 },
};

function renderInApp(sheet: ReactElement) {
  return render(<SafeAreaProvider initialMetrics={METRICS}>{sheet}</SafeAreaProvider>);
}

describe('Sheet', () => {
  it('shows its title and content when visible', async () => {
    await renderInApp(
      <Sheet visible onClose={() => {}} title="Add a payment">
        <Text>Form goes here</Text>
      </Sheet>,
    );

    expect(screen.getByText('Form goes here')).toBeOnTheScreen();
  });

  it('shows nothing until it is opened', async () => {
    await renderInApp(
      <Sheet visible={false} onClose={() => {}} title="Add a payment">
        <Text>Form goes here</Text>
      </Sheet>,
    );

    expect(screen.queryByText('Add a payment')).not.toBeOnTheScreen();
  });

  it('asks to close when the backdrop is tapped', async () => {
    const onClose = jest.fn();
    await renderInApp(
      <Sheet visible onClose={onClose} title="Add a payment">
        <Text>Form goes here</Text>
      </Sheet>,
    );

    await fireEvent.press(screen.getByLabelText('Close'));

    expect(onClose).toHaveBeenCalled();
  });

  it('asks to close from its Close link', async () => {
    const onClose = jest.fn();
    await renderInApp(
      <Sheet visible onClose={onClose} title="Add a payment">
        <Text>Form goes here</Text>
      </Sheet>,
    );

    await fireEvent.press(screen.getByRole('button', { name: 'Close' }));

    expect(onClose).toHaveBeenCalled();
  });

  it('shows its footer', async () => {
    await renderInApp(
      <Sheet visible onClose={() => {}} title="Add a payment" footer={<Text>Save</Text>}>
        <Text>Form goes here</Text>
      </Sheet>,
    );

    expect(screen.getByText('Save')).toBeOnTheScreen();
  });
});
