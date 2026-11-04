import { fireEvent, renderRouter, screen } from 'expo-router/testing-library';
import { Linking, Text } from 'react-native';

import { Markdown } from '@/docs/Markdown';

function renderSource(source: string) {
  return renderRouter({
    index: () => <Markdown source={source} />,
    'docs/payments': () => <Text>The payments guide</Text>,
  });
}

describe('Markdown', () => {
  it('draws a second-level heading as a heading', async () => {
    await renderSource('## Title');

    expect(screen.getByRole('heading', { name: 'Title' })).toBeOnTheScreen();
  });

  it('draws a third-level heading as a heading', async () => {
    await renderSource('### Title');

    expect(screen.getByRole('heading', { name: 'Title' })).toBeOnTheScreen();
  });

  it('joins a paragraph wrapped over several lines', async () => {
    await renderSource('one\ntwo');

    expect(screen.getByText('one two')).toBeOnTheScreen();
  });

  it('draws each paragraph on its own', async () => {
    await renderSource('one\n\ntwo');

    expect(screen.getByText('two')).toBeOnTheScreen();
  });

  it('keeps bold in with the words around it', async () => {
    await renderSource('a **b** c');

    expect(screen.getByText('a b c')).toBeOnTheScreen();
  });

  it('leaves punctuation unescaped', async () => {
    await renderSource('it\'s "this" & that');

    expect(screen.getByText('it\'s "this" & that')).toBeOnTheScreen();
  });

  it('numbers an ordered list', async () => {
    await renderSource('1. a\n2. b');

    expect(screen.getByText('2.')).toBeOnTheScreen();
  });

  it('marks a bullet list', async () => {
    await renderSource('- a\n- b');

    expect(screen.getAllByText('•')).toHaveLength(2);
  });

  it('joins a list item wrapped over several lines', async () => {
    await renderSource('- one\n  two');

    expect(screen.getByText('one two')).toBeOnTheScreen();
  });

  it('draws what a quote says, joined up', async () => {
    await renderSource('> one\n> two');

    expect(screen.getByText('one two')).toBeOnTheScreen();
  });

  it('draws a table’s header', async () => {
    await renderSource('| A | B |\n| --- | --- |\n| 1 | 2 |');

    expect(screen.getByText('B')).toBeOnTheScreen();
  });

  it('draws a table’s cells', async () => {
    await renderSource('| A | B |\n| --- | --- |\n| 1 | **2** |');

    expect(screen.getByText('2')).toBeOnTheScreen();
  });

  it('follows a link within the app', async () => {
    await renderSource('see [Payments](/docs/payments).');

    await fireEvent.press(screen.getByRole('link', { name: 'Payments' }));

    expect(await screen.findByText('The payments guide')).toBeOnTheScreen();
  });

  it('opens a link to the web outside the app', async () => {
    const open = jest.spyOn(Linking, 'openURL').mockResolvedValue(undefined);
    await renderSource('[Auth0](https://auth0.com)');

    await fireEvent.press(screen.getByRole('link', { name: 'Auth0' }));

    expect(open).toHaveBeenCalledWith('https://auth0.com');
  });

  it('draws a bold link', async () => {
    await renderSource('**[Payments](/docs/payments)**');

    expect(screen.getByRole('link', { name: 'Payments' })).toBeOnTheScreen();
  });

  it('leaves out what it doesn’t draw', async () => {
    await renderSource('---\n\nkept');

    expect(screen.getByText('kept')).toBeOnTheScreen();
  });
});
