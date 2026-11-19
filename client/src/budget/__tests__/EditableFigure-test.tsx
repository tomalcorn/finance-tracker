import { fireEvent, render, screen } from '@testing-library/react-native';

import { EditableFigure } from '@/budget/EditableFigure';

describe('EditableFigure', () => {
  it('reports the amount as it is typed, and that editing has ended', async () => {
    const onDraft = jest.fn();
    await render(
      <EditableFigure
        label="Planned"
        value={150}
        validate={(text) => (text.startsWith('-') ? 'Must not be negative' : undefined)}
        onSave={() => Promise.resolve()}
        onDraft={onDraft}
      />,
    );

    await fireEvent.press(screen.getByRole('button'));
    await fireEvent.changeText(screen.getByLabelText('Planned'), '200');
    expect(onDraft).toHaveBeenLastCalledWith(200);

    // An amount that can't be saved leaves the preview on the last one that could.
    await fireEvent.changeText(screen.getByLabelText('Planned'), '-5');
    expect(onDraft).toHaveBeenCalledTimes(1);

    await fireEvent.changeText(screen.getByLabelText('Planned'), '250');
    await fireEvent(screen.getByLabelText('Planned'), 'submitEditing');
    expect(onDraft).toHaveBeenLastCalledWith(null);
  });
});
