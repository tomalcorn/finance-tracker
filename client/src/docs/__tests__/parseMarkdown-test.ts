import { parseInlines, parseMarkdown } from '@/docs/parseMarkdown';

describe('parseInlines', () => {
  it('leaves plain text alone', () => {
    expect(parseInlines('just words')).toEqual([{ kind: 'text', text: 'just words' }]);
  });

  it('finds bold in the middle of a line', () => {
    expect(parseInlines('a **b** c')).toEqual([
      { kind: 'text', text: 'a ' },
      { kind: 'strong', text: 'b' },
      { kind: 'text', text: ' c' },
    ]);
  });

  it('finds italics', () => {
    expect(parseInlines('*b*')).toEqual([{ kind: 'emphasis', text: 'b' }]);
  });

  it('finds a link', () => {
    expect(parseInlines('see [Payments](/docs/payments).')).toEqual([
      { kind: 'text', text: 'see ' },
      { kind: 'link', text: 'Payments', href: '/docs/payments' },
      { kind: 'text', text: '.' },
    ]);
  });

  it('leaves a lone asterisk alone', () => {
    expect(parseInlines('2 * 3')).toEqual([{ kind: 'text', text: '2 * 3' }]);
  });
});

describe('parseMarkdown', () => {
  it('reads a second-level heading', () => {
    expect(parseMarkdown('## Title')).toEqual([{ kind: 'heading', level: 2, text: 'Title' }]);
  });

  it('reads a third-level heading', () => {
    expect(parseMarkdown('### Title')).toEqual([{ kind: 'heading', level: 3, text: 'Title' }]);
  });

  it('joins a wrapped paragraph', () => {
    expect(parseMarkdown('one\ntwo')).toEqual([
      { kind: 'paragraph', inlines: [{ kind: 'text', text: 'one two' }] },
    ]);
  });

  it('separates paragraphs at a blank line', () => {
    expect(parseMarkdown('one\n\ntwo')).toHaveLength(2);
  });

  it('ends a paragraph at a list', () => {
    expect(parseMarkdown('one\n- two').map((block) => block.kind)).toEqual(['paragraph', 'list']);
  });

  it('reads a bullet list', () => {
    expect(parseMarkdown('- a\n- b')).toEqual([
      {
        kind: 'list',
        ordered: false,
        items: [[{ kind: 'text', text: 'a' }], [{ kind: 'text', text: 'b' }]],
      },
    ]);
  });

  it('reads a numbered list', () => {
    expect(parseMarkdown('1. a\n2. b')).toEqual([
      {
        kind: 'list',
        ordered: true,
        items: [[{ kind: 'text', text: 'a' }], [{ kind: 'text', text: 'b' }]],
      },
    ]);
  });

  it('joins an item wrapped onto an indented line', () => {
    expect(parseMarkdown('- one\n  two')).toEqual([
      { kind: 'list', ordered: false, items: [[{ kind: 'text', text: 'one two' }]] },
    ]);
  });

  it('joins a wrapped quote', () => {
    expect(parseMarkdown('> one\n> two')).toEqual([
      { kind: 'quote', inlines: [{ kind: 'text', text: 'one two' }] },
    ]);
  });

  it('reads a table', () => {
    expect(parseMarkdown('| A | B |\n| --- | --- |\n| 1 | 2 |')).toEqual([
      {
        kind: 'table',
        header: [[{ kind: 'text', text: 'A' }], [{ kind: 'text', text: 'B' }]],
        rows: [[[{ kind: 'text', text: '1' }], [{ kind: 'text', text: '2' }]]],
      },
    ]);
  });

  it('reads inline formatting in a table cell', () => {
    const [table] = parseMarkdown('| A |\n| --- |\n| **b** |');

    expect(table).toMatchObject({ rows: [[[{ kind: 'strong', text: 'b' }]]] });
  });
});
