import { fireEvent, render, screen } from '@testing-library/react-native';
import { useState } from 'react';
import { Platform, View } from 'react-native';

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

/** Opens the field's calendar. */
function open() {
  return fireEvent.press(screen.getByRole('button', { name: /^Date, / }));
}

/** Presses a key in the grid with this label, e.g. `November 2026` or `Months of 2026`. */
function keyDown(grid: string, key: string) {
  return fireEvent(screen.getByLabelText(grid, { exact: true }), 'keyDown', {
    key,
    preventDefault() {},
  });
}

/** Presses Escape with focus on whatever has this label. Returns the event, to see where it went. */
async function escape(label: string) {
  const event = { key: 'Escape', stopPropagation: jest.fn() };
  await fireEvent(screen.getByLabelText(label, { exact: true }), 'keyUp', event);
  return event;
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

    await open();
    expect(screen.getByText('September 2026')).toBeTruthy();

    await fireEvent.press(day('2026-09-21'));

    expect(onChange).toHaveBeenCalledWith('2026-09-21');
    expect(screen.queryByText('September 2026')).toBeNull();
    expect(screen.getByRole('button', { name: 'Date, Mon 21 Sept' })).toBeTruthy();
  });

  it('moves between months', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();

    await fireEvent.press(screen.getByRole('button', { name: 'Next month' }));
    expect(screen.getByText('December 2026')).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: 'Previous month' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Previous month' }));
    expect(screen.getByText('October 2026')).toBeTruthy();
  });

  it('marks today on the calendar', async () => {
    await render(<Harness initial="2026-11-01" />);
    await open();

    expect(screen.getByRole('button', { name: /12 November 2026, today$/ })).toHaveProp(
      'aria-current',
      'date',
    );
  });

  it('moves the focused day with the arrow and Page keys', async () => {
    const onChange = jest.fn();
    await render(<Harness initial="2026-11-30" onChange={onChange} />);
    await open();

    await keyDown('November 2026', 'ArrowRight');
    expect(screen.getByText('December 2026')).toBeTruthy();

    // The day the keys reached is the one in the tab order.
    expect(day('2026-12-01')).toHaveProp('focusable', true);
    expect(day('2026-12-02')).toHaveProp('focusable', false);

    await keyDown('December 2026', 'PageUp');
    expect(screen.getByText('November 2026')).toBeTruthy();
    expect(day('2026-11-01')).toHaveProp('focusable', true);
  });

  it('closes the calendar on Escape', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();

    await escape('November 2026');

    expect(screen.queryByLabelText('November 2026', { exact: true })).toBeNull();
  });

  it('closes on Escape from the header too', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();

    await escape('Next month');

    expect(screen.queryByLabelText('November 2026', { exact: true })).toBeNull();
  });

  it('keeps Escape to itself, so a sheet around it stays open', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();

    const event = await escape('November 2026');

    expect(event.stopPropagation).toHaveBeenCalled();
  });

  it('closes the calendar when a quick pick sets the date', async () => {
    await render(<Harness initial="2026-09-15" />);
    await open();

    await fireEvent.press(screen.getByRole('button', { name: 'Date: yesterday' }));

    expect(screen.queryByText('September 2026')).toBeNull();
    expect(screen.getByRole('button', { name: 'Date, Yesterday, Wed 11 Nov' })).toBeTruthy();
  });

  it('opens the year’s months from the month’s banner, and picks one', async () => {
    const onChange = jest.fn();
    await render(<Harness initial="2026-11-12" onChange={onChange} />);
    await open();

    await fireEvent.press(screen.getByRole('button', { name: 'November 2026, choose a month' }));

    expect(screen.getByText('2026')).toBeTruthy();
    expect(screen.getAllByRole('button', { name: /^\w+ 2026/ })).toHaveLength(12);
    expect(screen.getByRole('button', { name: 'November 2026, current' })).toHaveProp(
      'aria-current',
      'date',
    );

    await fireEvent.press(screen.getByRole('button', { name: 'March 2026' }));

    expect(screen.getByText('March 2026')).toBeTruthy();
    expect(onChange).not.toHaveBeenCalled();
    await fireEvent.press(day('2026-03-14'));
    expect(onChange).toHaveBeenCalledWith('2026-03-14');
  });

  it('steps through years on the months page', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();
    await fireEvent.press(screen.getByRole('button', { name: /choose a month$/ }));

    await fireEvent.press(screen.getByRole('button', { name: 'Previous year' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Previous year' }));

    expect(screen.getByText('2024')).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: 'February 2024' }));
    expect(screen.getByText('February 2024')).toBeTruthy();
  });

  it('opens a page of years from the year’s banner, and pages back through them', async () => {
    const onChange = jest.fn();
    await render(<Harness initial="2026-11-12" onChange={onChange} />);
    await open();
    await fireEvent.press(screen.getByRole('button', { name: /choose a month$/ }));

    await fireEvent.press(screen.getByRole('button', { name: '2026, choose a year' }));

    expect(screen.getByText('2016 – 2027')).toBeTruthy();
    expect(screen.getByRole('button', { name: '2026, current' })).toHaveProp(
      'aria-current',
      'date',
    );

    await fireEvent.press(screen.getByRole('button', { name: 'Earlier years' }));
    expect(screen.getByText('2004 – 2015')).toBeTruthy();

    await fireEvent.press(screen.getByRole('button', { name: '2011' }));
    expect(screen.getByText('2011')).toBeTruthy();
    await fireEvent.press(screen.getByRole('button', { name: 'June 2011' }));
    await fireEvent.press(day('2011-06-03'));

    expect(onChange).toHaveBeenCalledWith('2011-06-03');
  });

  it('keeps the month it was on when another year is picked', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();
    await fireEvent.press(screen.getByRole('button', { name: /choose a month$/ }));
    await fireEvent.press(screen.getByRole('button', { name: /choose a year$/ }));

    await fireEvent.press(screen.getByRole('button', { name: '2025' }));

    expect(screen.getByLabelText('November 2025')).toHaveProp('focusable', true);
    expect(screen.getByLabelText('January 2025')).toHaveProp('focusable', false);
  });

  it('marks the chosen month and year', async () => {
    await render(<Harness initial="2025-04-20" />);
    await open();
    await fireEvent.press(screen.getByRole('button', { name: 'April 2025, choose a month' }));

    expect(screen.getByLabelText('April 2025').parent).toHaveProp('aria-selected', true);
    expect(screen.getByLabelText('May 2025').parent).toHaveProp('aria-selected', false);

    await fireEvent.press(screen.getByRole('button', { name: '2025, choose a year' }));
    expect(screen.getByLabelText('2025').parent).toHaveProp('aria-selected', true);
  });

  it('steps back out a level at a time on Escape', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();
    await fireEvent.press(screen.getByRole('button', { name: /choose a month$/ }));
    await fireEvent.press(screen.getByRole('button', { name: /choose a year$/ }));

    await escape('Years 2016 to 2027');
    expect(screen.getByLabelText('Months of 2026', { exact: true })).toBeTruthy();
    await escape('Months of 2026');
    expect(screen.getByLabelText('November 2026', { exact: true })).toBeTruthy();
  });

  it('moves between tiles with the arrow keys, onto the next page at an edge', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();
    await fireEvent.press(screen.getByRole('button', { name: /choose a month$/ }));

    await keyDown('Months of 2026', 'ArrowUp');
    expect(screen.getByLabelText('August 2026')).toHaveProp('focusable', true);

    await keyDown('Months of 2026', 'ArrowDown');
    await keyDown('Months of 2026', 'ArrowDown');
    expect(screen.getByText('2027')).toBeTruthy();
    expect(screen.getByLabelText('February 2027')).toHaveProp('focusable', true);
  });

  it('moves between years with the arrow keys, onto the next page at an edge', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();
    await fireEvent.press(screen.getByRole('button', { name: /choose a month$/ }));
    await fireEvent.press(screen.getByRole('button', { name: /choose a year$/ }));

    await keyDown('Years 2016 to 2027', 'ArrowDown');

    expect(screen.getByText('2028 – 2039')).toBeTruthy();
    expect(screen.getByLabelText('2029')).toHaveProp('focusable', true);
  });

  it('keeps the tab order on the page when the arrows turn it', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();
    await fireEvent.press(screen.getByRole('button', { name: /choose a month$/ }));
    await fireEvent.press(screen.getByRole('button', { name: /choose a year$/ }));

    await fireEvent.press(screen.getByRole('button', { name: 'Earlier years' }));

    expect(screen.getByLabelText('2014')).toHaveProp('focusable', true);
  });

  it('stops at the first year it reaches', async () => {
    const onChange = jest.fn();
    await render(<Harness initial="2026-11-12" onChange={onChange} />);
    await open();
    await fireEvent.press(screen.getByRole('button', { name: /choose a month$/ }));
    await fireEvent.press(screen.getByRole('button', { name: /choose a year$/ }));

    const earlier = () => screen.getByRole('button', { name: 'Earlier years' });
    for (let page = 0; page < 10; page += 1) await fireEvent.press(earlier());

    expect(screen.getByText('1900 – 1911')).toBeTruthy();
    expect(earlier()).toBeDisabled();

    await fireEvent.press(screen.getByRole('button', { name: '1900' }));
    expect(screen.getByRole('button', { name: 'Previous year' })).toBeDisabled();
    await fireEvent.press(screen.getByRole('button', { name: 'January 1900' }));
    expect(screen.getByRole('button', { name: 'Previous month' })).toBeDisabled();

    await fireEvent.press(day('1900-01-01'));
    expect(onChange).toHaveBeenCalledWith('1900-01-01');
  });

  it('opens on today when the date is one it doesn’t reach', async () => {
    await render(<Harness initial="0026-11-12" />);
    await open();

    expect(screen.getByLabelText('November 2026', { exact: true })).toBeTruthy();
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

    await open();
    expect(box()).toHaveStyle({ borderColor: LIGHT.accent });

    await rerender(
      <DateField label="Date" value="2026-11-12" onChange={() => {}} error="Pick a date" />,
    );
    expect(box()).toHaveStyle({ borderColor: LIGHT.negative });
    expect(screen.getByText('Pick a date')).toBeTruthy();
  });
});

describe('DateField on the web', () => {
  /** The label of whatever last took focus. */
  let focus: string | undefined;

  beforeEach(() => {
    focus = undefined;
    jest.replaceProperty(Platform, 'OS', 'web');
    jest.spyOn(View.prototype, 'focus').mockImplementation(function (this: View) {
      focus = this.props.accessibilityLabel;
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('moves focus onto the chosen day as the calendar opens', async () => {
    await render(<Harness initial="2026-11-10" />);
    await open();

    expect(focus).toBe(formatLongDay('2026-11-10'));
  });

  it('moves focus with the keys, onto another month too', async () => {
    await render(<Harness initial="2026-11-30" />);
    await open();

    await keyDown('November 2026', 'ArrowRight');

    expect(focus).toBe(formatLongDay('2026-12-01'));
  });

  it('leaves focus on an arrow that pages, even after a key that moved nothing', async () => {
    // 9 November 2026 is a Monday, where Home has nowhere to go.
    await render(<Harness initial="2026-11-09" />);
    await open();
    await keyDown('November 2026', 'Home');
    focus = 'Next month';

    await fireEvent.press(screen.getByRole('button', { name: 'Next month' }));

    expect(screen.getByText('December 2026')).toBeTruthy();
    expect(focus).toBe('Next month');
  });

  it('moves focus onto each grid it opens', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();

    await fireEvent.press(screen.getByRole('button', { name: /choose a month$/ }));
    expect(focus).toBe('November 2026, current');

    await fireEvent.press(screen.getByRole('button', { name: /choose a year$/ }));
    expect(focus).toBe('2026, current');
  });

  it('gives focus back to the field when the calendar closes', async () => {
    await render(<Harness initial="2026-11-12" />);
    await open();

    await escape('November 2026');

    expect(focus).toBe('Date, Today, Thu 12 Nov');
  });
});
