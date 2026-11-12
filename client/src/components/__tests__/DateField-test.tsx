import { fireEvent, render, screen } from '@testing-library/react-native';
import { useState } from 'react';

import { DateField, type DateFieldProps } from '@/components/DateField';
import { formatLongDay } from '@/theme/formatDate';
import { LIGHT } from '@/theme/tokens';

/** A `DateField` that keeps its own value, as a form would. */
function Harness({ initial, ...props }: Partial<DateFieldProps> & { initial: string }) {
  const [value, setValue] = useState(initial);
  return (
    <DateField
      label="Date"
      {...props}
      value={value}
      onChange={(date) => {
        setValue(date);
        props.onChange?.(date);
      }}
    />
  );
}

/** A calendar day's button, named as the platform spells the date out. */
function day(date: string) {
  return screen.getByRole('button', { name: new RegExp(`^${formatLongDay(date)}`) });
}

/** The calendar's grid of days, labelled with its month. */
function grid(month: string) {
  return screen.getByLabelText(month, { exact: true });
}

beforeEach(() => {
  jest.useFakeTimers({ now: new Date(2026, 10, 12, 9), advanceTimers: true });
});

afterEach(() => {
  jest.useRealTimers();
});

describe('DateField', () => {
  it('shows the date in words', async () => {
    await render(<Harness initial="2026-11-10" />);

    expect(screen.getByRole('button', { name: 'Date, Tue 10 Nov' })).toBeTruthy();
  });

  it('calls today and yesterday by name', async () => {
    await render(<Harness initial="2026-11-11" />);

    expect(screen.getByRole('button', { name: 'Date, Yesterday, Wed 11 Nov' })).toBeTruthy();
  });

  it('sets today or yesterday in one tap', async () => {
    const onChange = jest.fn();
    await render(<Harness initial="2026-11-01" onChange={onChange} />);

    await fireEvent.press(screen.getByRole('button', { name: 'Date: today' }));
    expect(onChange).toHaveBeenLastCalledWith('2026-11-12');

    await fireEvent.press(screen.getByRole('button', { name: 'Date: yesterday' }));
    expect(onChange).toHaveBeenLastCalledWith('2026-11-11');
  });

  it('marks the quick pick that matches the date', async () => {
    await render(<Harness initial="2026-11-12" />);

    expect(screen.getByRole('button', { name: 'Date: today' })).toHaveProp('aria-pressed', true);
    expect(screen.getByRole('button', { name: 'Date: yesterday' })).toHaveProp(
      'aria-pressed',
      false,
    );
  });

  it('leaves the quick picks out when asked', async () => {
    await render(<Harness initial="2026-11-12" quickPicks={false} />);

    expect(screen.queryByRole('button', { name: 'Date: today' })).toBeNull();
  });

  it('opens a calendar on the chosen month and picks a day from it', async () => {
    const onChange = jest.fn();
    await render(<Harness initial="2026-09-15" onChange={onChange} />);

    await fireEvent.press(screen.getByRole('button', { name: /^Date, / }));
    expect(screen.getByText('September 2026')).toBeTruthy();

    await fireEvent.press(day('2026-09-21'));

    expect(onChange).toHaveBeenCalledWith('2026-09-21');
    expect(screen.queryByText('September 2026')).toBeNull();
    expect(screen.getByRole('button', { name: 'Date, Mon 21 Sept' })).toBeTruthy();
  });

  it('moves between months', async () => {
    await render(<Harness initial="2026-11-12" />);
    await fireEvent.press(screen.getByRole('button', { name: /^Date, / }));

    await fireEvent.press(screen.getByRole('button', { name: 'Next month' }));
    expect(screen.getByText('December 2026')).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: 'Previous month' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Previous month' }));
    expect(screen.getByText('October 2026')).toBeTruthy();
  });

  it('marks today on the calendar', async () => {
    await render(<Harness initial="2026-11-01" />);
    await fireEvent.press(screen.getByRole('button', { name: /^Date, / }));

    expect(screen.getByRole('button', { name: /12 November 2026, today$/ })).toHaveProp(
      'aria-current',
      'date',
    );
  });

  it('moves the focused day with the arrow and Page keys', async () => {
    const onChange = jest.fn();
    await render(<Harness initial="2026-11-30" onChange={onChange} />);
    await fireEvent.press(screen.getByRole('button', { name: /^Date, / }));

    const key = (name: string, month: string) =>
      fireEvent(grid(month), 'keyDown', { key: name, preventDefault() {} });
    await key('ArrowRight', 'November 2026');
    expect(screen.getByText('December 2026')).toBeTruthy();

    // The day the keys reached is the one in the tab order.
    expect(day('2026-12-01')).toHaveProp('focusable', true);
    expect(day('2026-12-02')).toHaveProp('focusable', false);

    await key('PageUp', 'December 2026');
    expect(screen.getByText('November 2026')).toBeTruthy();
    expect(day('2026-11-01')).toHaveProp('focusable', true);
  });

  it('closes the calendar on Escape', async () => {
    await render(<Harness initial="2026-11-12" />);
    await fireEvent.press(screen.getByRole('button', { name: /^Date, / }));

    await fireEvent(grid('November 2026'), 'keyDown', { key: 'Escape', preventDefault() {} });

    expect(screen.queryByLabelText('November 2026', { exact: true })).toBeNull();
  });

  it('can be cleared when the date is optional', async () => {
    const onChange = jest.fn();
    await render(<Harness initial="2026-12-01" optional onChange={onChange} />);

    await fireEvent.press(screen.getByRole('button', { name: 'Clear date' }));

    expect(onChange).toHaveBeenCalledWith('');
    expect(screen.getByRole('button', { name: 'Date, No date' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Clear date' })).toBeNull();
  });

  it('has no Clear when the date is required', async () => {
    await render(<Harness initial="2026-12-01" />);

    expect(screen.queryByRole('button', { name: 'Clear date' })).toBeNull();
  });

  it('outlines itself in the accent while open, and in the negative colour for an error', async () => {
    const { rerender } = await render(
      <DateField label="Date" value="2026-11-12" onChange={() => {}} />,
    );
    const box = () => screen.getByRole('button', { name: /^Date, / }).parent;

    await fireEvent.press(screen.getByRole('button', { name: /^Date, / }));
    expect(box()).toHaveStyle({ borderColor: LIGHT.accent });

    await rerender(
      <DateField label="Date" value="2026-11-12" onChange={() => {}} error="Pick a date" />,
    );
    expect(box()).toHaveStyle({ borderColor: LIGHT.negative });
    expect(screen.getByText('Pick a date')).toBeTruthy();
  });
});
