import { fireEvent, render, screen } from '@testing-library/react-native';

import { DateField } from '@/components/DateField.web';
import { LIGHT } from '@/theme/tokens';

/** Sets what the browser says the main pointer is: a finger (coarse) or a mouse. */
function pointer(kind: 'coarse' | 'fine') {
  window.matchMedia = jest.fn().mockReturnValue({
    matches: kind === 'coarse',
    addEventListener() {},
    removeEventListener() {},
  });
}

/** The browser's own date input, laid over the field. */
function dateInput() {
  const [input] = screen.container.queryAll((element) => element.type === 'input');
  if (!input) throw new Error('No date input was drawn.');
  return input;
}

beforeEach(() => {
  jest.useFakeTimers({ now: new Date(2026, 10, 12, 9), advanceTimers: true });
});

afterEach(() => {
  jest.useRealTimers();
});

describe('DateField in a browser, on a touch screen', () => {
  beforeEach(() => pointer('coarse'));

  it('lays the browser’s date input over the field, named by its label', async () => {
    await render(<DateField label="Date" value="2026-11-10" onChange={() => {}} />);

    const input = dateInput();
    expect(input.props).toMatchObject({ type: 'date', value: '2026-11-10' });
    expect(screen.getByText('Date')).toHaveProp('nativeID', input.props['aria-labelledby']);
    // The words under the input are for the eye only: the input speaks for the field.
    expect(screen.getByText('Tue 10 Nov', { includeHiddenElements: true })).toBeTruthy();
    expect(screen.queryByText('Tue 10 Nov')).toBeNull();
  });

  it('takes the date the browser’s picker gives', async () => {
    const onChange = jest.fn();
    await render(<DateField label="Date" value="2026-11-10" onChange={onChange} />);

    await fireEvent(dateInput(), 'change', { target: { value: '2026-12-25' } });

    expect(onChange).toHaveBeenCalledWith('2026-12-25');
  });

  it('keeps the quick picks and Clear', async () => {
    const onChange = jest.fn();
    await render(<DateField label="Ends" value="2026-11-10" onChange={onChange} optional />);

    await fireEvent.press(screen.getByRole('button', { name: 'Ends: today' }));
    expect(onChange).toHaveBeenLastCalledWith('2026-11-12');

    await fireEvent.press(screen.getByRole('button', { name: 'Clear ends' }));
    expect(onChange).toHaveBeenLastCalledWith('');
  });

  it('outlines the field while its input has focus, and for an error', async () => {
    const { rerender } = await render(<DateField label="Date" value="" onChange={() => {}} />);
    const box = () => dateInput().parent;

    await fireEvent(dateInput(), 'focus');
    expect(box()).toHaveStyle({ borderColor: LIGHT.accent });

    await rerender(<DateField label="Date" value="" onChange={() => {}} error="Pick a date" />);
    expect(box()).toHaveStyle({ borderColor: LIGHT.negative });
  });
});

describe('DateField in a browser, with a mouse', () => {
  beforeEach(() => pointer('fine'));

  it('opens the app’s calendar, and draws no date input', async () => {
    await render(<DateField label="Date" value="2026-11-10" onChange={() => {}} />);

    await fireEvent.press(screen.getByRole('button', { name: 'Date, Tue 10 Nov' }));

    expect(screen.getByLabelText('November 2026', { exact: true })).toBeTruthy();
    expect(screen.container.queryAll((element) => element.type === 'input')).toHaveLength(0);
  });
});
