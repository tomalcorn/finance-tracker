import { fireEvent, render, screen } from '@testing-library/react-native';

import { TextField } from '@/components/TextField';
import { LIGHT } from '@/theme/tokens';

describe('TextField', () => {
  it('has no outline until it is focused', async () => {
    await render(<TextField label="Name" />);

    expect(screen.getByLabelText('Name')).toHaveStyle({ borderColor: 'transparent' });
  });

  it('outlines itself in the accent while focused', async () => {
    await render(<TextField label="Name" />);

    await fireEvent(screen.getByLabelText('Name'), 'focus');

    expect(screen.getByLabelText('Name')).toHaveStyle({ borderColor: LIGHT.accent });
  });

  it('drops the outline again when it loses focus', async () => {
    await render(<TextField label="Name" />);

    await fireEvent(screen.getByLabelText('Name'), 'focus');
    await fireEvent(screen.getByLabelText('Name'), 'blur');

    expect(screen.getByLabelText('Name')).toHaveStyle({ borderColor: 'transparent' });
  });

  it('keeps the error outline while focused', async () => {
    await render(<TextField label="Name" error="Give it a name" />);

    await fireEvent(screen.getByLabelText('Name'), 'focus');

    expect(screen.getByLabelText('Name')).toHaveStyle({ borderColor: LIGHT.negative });
  });

  it('still calls its own focus handler', async () => {
    const onFocus = jest.fn();
    await render(<TextField label="Name" onFocus={onFocus} />);

    await fireEvent(screen.getByLabelText('Name'), 'focus');

    expect(onFocus).toHaveBeenCalled();
  });
});
