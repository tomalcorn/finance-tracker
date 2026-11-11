import { fireEvent, render, screen } from '@testing-library/react-native';
import { StyleSheet } from 'react-native';

import { SelectField } from '@/components/SelectField';
import { LIGHT } from '@/theme/tokens';

const OPTIONS = [
  { value: 'groceries', label: 'Groceries' },
  { value: 'transport', label: 'Transport' },
];

/** The outlined box around the field's button: its nearest ancestor with a border. */
function fieldBox() {
  let element = screen.getByRole('button', { name: 'Category' }).parent;
  while (element && StyleSheet.flatten(element.props.style)?.borderWidth === undefined) {
    element = element.parent;
  }
  if (!element) throw new Error('No outlined box around the field');
  return element;
}

describe('SelectField', () => {
  it('has no outline until it is focused', async () => {
    await render(
      <SelectField label="Category" value={null} options={OPTIONS} onChange={() => {}} />,
    );

    expect(fieldBox()).toHaveStyle({ borderColor: 'transparent' });
  });

  it('outlines itself in the accent while focused', async () => {
    await render(
      <SelectField label="Category" value={null} options={OPTIONS} onChange={() => {}} />,
    );

    await fireEvent(screen.getByRole('button', { name: 'Category' }), 'focus');

    expect(fieldBox()).toHaveStyle({ borderColor: LIGHT.accent });
  });

  it('outlines itself in the accent while open', async () => {
    await render(
      <SelectField label="Category" value={null} options={OPTIONS} onChange={() => {}} />,
    );

    await fireEvent.press(screen.getByRole('button', { name: 'Category' }));

    expect(fieldBox()).toHaveStyle({ borderColor: LIGHT.accent });
  });

  it('keeps the error outline while focused', async () => {
    await render(
      <SelectField
        label="Category"
        value={null}
        options={OPTIONS}
        onChange={() => {}}
        error="Choose a category"
      />,
    );

    await fireEvent(screen.getByRole('button', { name: 'Category' }), 'focus');

    expect(fieldBox()).toHaveStyle({ borderColor: LIGHT.negative });
  });
});
