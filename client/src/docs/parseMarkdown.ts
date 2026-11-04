/** A run of text in a line: plain, bold, italic, or a link. */
export type Inline =
  | { kind: 'text'; text: string }
  | { kind: 'strong'; text: string }
  | { kind: 'emphasis'; text: string }
  | { kind: 'link'; text: string; href: string };

/** One block of a page. */
export type Block =
  | { kind: 'heading'; level: 2 | 3; text: string }
  | { kind: 'paragraph'; inlines: Inline[] }
  | { kind: 'list'; ordered: boolean; items: Inline[][] }
  | { kind: 'table'; header: Inline[][]; rows: Inline[][][] }
  | { kind: 'quote'; inlines: Inline[] };

const INLINE = /\*\*(.+?)\*\*|\*(.+?)\*|\[(.+?)\]\((.+?)\)/g;
const HEADING = /^(#{2,3}) (.+)$/;
const BULLET = /^- (.+)$/;
const NUMBERED = /^\d+\. (.+)$/;
const INDENTED = /^ {2,}(\S.*)$/;
const QUOTE = /^> ?(.*)$/;
const TABLE_ROW = /^\|(.+)\|$/;
const TABLE_RULE = /^\|[\s|:-]+\|$/;

/** Split a line's text into plain, bold, italic and linked runs. */
export function parseInlines(text: string): Inline[] {
  const inlines: Inline[] = [];
  let end = 0;
  for (const match of text.matchAll(INLINE)) {
    if (match.index > end) inlines.push({ kind: 'text', text: text.slice(end, match.index) });
    const [whole, strong, emphasis, linkText, href] = match;
    if (strong !== undefined) inlines.push({ kind: 'strong', text: strong });
    else if (emphasis !== undefined) inlines.push({ kind: 'emphasis', text: emphasis });
    else if (linkText !== undefined && href !== undefined) {
      inlines.push({ kind: 'link', text: linkText, href });
    }
    end = match.index + whole.length;
  }
  if (end < text.length) inlines.push({ kind: 'text', text: text.slice(end) });
  return inlines;
}

function cellsOf(row: string): Inline[][] {
  return row
    .slice(1, -1)
    .split('|')
    .map((cell) => parseInlines(cell.trim()));
}

/**
 * Parse the markdown the guides are written in, which is a deliberately small part of it: `##` and
 * `###` headings, paragraphs, flat bullet and numbered lists, tables and quotes, with bold, italic
 * and links inside them. A line's wrapping is not significant.
 */
export function parseMarkdown(source: string): Block[] {
  const lines = source.split('\n');
  const blocks: Block[] = [];
  let index = 0;

  /** Take the lines from here that match, with any indented continuation joined onto each. */
  function gather(pattern: RegExp): string[] {
    const gathered: string[] = [];
    for (; index < lines.length; index += 1) {
      const line = lines[index] ?? '';
      const match = pattern.exec(line);
      const continuation = INDENTED.exec(line);
      if (match?.[1] !== undefined) gathered.push(match[1]);
      else if (match) gathered.push('');
      else if (continuation?.[1] && gathered.length > 0) {
        gathered[gathered.length - 1] += ` ${continuation[1]}`;
      } else break;
    }
    return gathered;
  }

  while (index < lines.length) {
    const line = lines[index] ?? '';
    const heading = HEADING.exec(line);

    if (line.trim() === '') {
      index += 1;
    } else if (heading?.[1] && heading[2]) {
      blocks.push({ kind: 'heading', level: heading[1].length === 2 ? 2 : 3, text: heading[2] });
      index += 1;
    } else if (BULLET.test(line)) {
      const items = gather(BULLET).map(parseInlines);
      blocks.push({ kind: 'list', ordered: false, items });
    } else if (NUMBERED.test(line)) {
      const items = gather(NUMBERED).map(parseInlines);
      blocks.push({ kind: 'list', ordered: true, items });
    } else if (QUOTE.test(line)) {
      blocks.push({ kind: 'quote', inlines: parseInlines(gather(QUOTE).join(' ')) });
    } else if (TABLE_ROW.test(line) && TABLE_RULE.test(lines[index + 1] ?? '')) {
      const header = cellsOf(line);
      index += 2;
      const rows: Inline[][][] = [];
      for (; TABLE_ROW.test(lines[index] ?? ''); index += 1) {
        rows.push(cellsOf(lines[index] ?? ''));
      }
      blocks.push({ kind: 'table', header, rows });
    } else {
      const text: string[] = [];
      for (; index < lines.length; index += 1) {
        const next = lines[index] ?? '';
        const starts = [HEADING, BULLET, NUMBERED, QUOTE, TABLE_ROW].some((block) =>
          block.test(next),
        );
        if (next.trim() === '' || (starts && text.length > 0)) break;
        text.push(next.trim());
      }
      blocks.push({ kind: 'paragraph', inlines: parseInlines(text.join(' ')) });
    }
  }
  return blocks;
}
