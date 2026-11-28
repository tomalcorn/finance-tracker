import { act, fireEvent, render, renderHook, screen } from '@testing-library/react-native';
import { Text } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { Button } from '@/components/Button';
import { TOAST_MS, ToastProvider, useToast } from '@/components/Toast';
import { MissingProviderError } from '@/hooks/MissingProviderError';

const METRICS = {
  frame: { x: 0, y: 0, width: 390, height: 844 },
  insets: { top: 47, left: 0, right: 0, bottom: 34 },
};

/** A screen that shows a toast from each of its buttons. */
function Notifier({ onUndo = () => {} }: { onUndo?: () => void }) {
  const { notify } = useToast();
  return (
    <>
      <Text>Screen content</Text>
      <Button title="Save" onPress={() => notify('Saved')} />
      <Button
        title="Delete"
        onPress={() => notify('Deleted', { label: 'Undo', onPress: onUndo })}
      />
    </>
  );
}

function renderScreen(onUndo?: () => void) {
  return render(
    <SafeAreaProvider initialMetrics={METRICS}>
      <ToastProvider>
        <Notifier onUndo={onUndo} />
      </ToastProvider>
    </SafeAreaProvider>,
  );
}

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

describe('ToastProvider', () => {
  it('shows its screen', async () => {
    await renderScreen();

    expect(screen.getByText('Screen content')).toBeOnTheScreen();
  });

  it('shows what a screen notifies', async () => {
    await renderScreen();

    await fireEvent.press(screen.getByText('Save'));

    expect(screen.getByText('Saved')).toBeOnTheScreen();
  });

  it('shows the latest toast in place of the one before', async () => {
    await renderScreen();
    await fireEvent.press(screen.getByText('Save'));

    await fireEvent.press(screen.getByText('Delete'));

    expect(screen.queryByText('Saved')).not.toBeOnTheScreen();
  });

  it('takes a toast’s action when it is pressed', async () => {
    const onUndo = jest.fn();
    await renderScreen(onUndo);
    await fireEvent.press(screen.getByText('Delete'));

    await fireEvent.press(screen.getByText('Undo'));

    expect(onUndo).toHaveBeenCalled();
  });

  it('dismisses a toast once its action is taken', async () => {
    await renderScreen();
    await fireEvent.press(screen.getByText('Delete'));

    await fireEvent.press(screen.getByText('Undo'));

    expect(screen.queryByText('Deleted')).not.toBeOnTheScreen();
  });

  it('dismisses a toast after a while', async () => {
    jest.useFakeTimers();
    await renderScreen();
    await fireEvent.press(screen.getByText('Save'));

    await act(async () => jest.advanceTimersByTime(TOAST_MS));

    expect(screen.queryByText('Saved')).not.toBeOnTheScreen();
  });
});

describe('useToast', () => {
  it('names the provider it needs when used outside one', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});

    await expect(renderHook(() => useToast())).rejects.toMatchObject({
      constructor: MissingProviderError,
      hook: 'useToast',
      provider: 'ToastProvider',
    });
  });
});
