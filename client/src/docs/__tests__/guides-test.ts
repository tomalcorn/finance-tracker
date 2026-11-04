import { lexer, walkTokens, type MarkedToken, type Token } from 'marked';

import { GUIDES, guideBySlug } from '@/docs/guides';

const DRAWN_BLOCKS = ['space', 'heading', 'paragraph', 'list', 'blockquote', 'table'];

/** Every token in a guide, at any depth, with the guide it came from. */
const tokens: { slug: string; token: MarkedToken }[] = GUIDES.flatMap((guide) => {
  const found: Token[] = [];
  walkTokens(lexer(guide.body), (token) => {
    found.push(token);
  });
  return found.map((token) => ({ slug: guide.slug, token: token as MarkedToken }));
});

describe('GUIDES', () => {
  it('has all nine', () => {
    expect(GUIDES).toHaveLength(9);
  });

  it('runs in order', () => {
    expect(GUIDES.map((guide) => guide.order)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9]);
  });

  it('gives every guide its own slug', () => {
    expect(new Set(GUIDES.map((guide) => guide.slug)).size).toBe(GUIDES.length);
  });

  it.each(GUIDES.map((guide) => [guide.slug]))('%s has a slug safe in an address', (slug) => {
    expect(slug).toMatch(/^[a-z][a-z_]*$/);
  });

  it.each(GUIDES.map((guide) => [guide.slug, guide.body]))(
    '%s only uses blocks that can be drawn',
    (_slug, body) => {
      const undrawn = lexer(body).filter((token) => !DRAWN_BLOCKS.includes(token.type));

      expect(undrawn.map((token) => token.raw)).toEqual([]);
    },
  );

  it('leaves no markdown unread', () => {
    const unread = tokens.filter(
      ({ token }) => token.type === 'text' && !token.tokens && /\*\*|\]\(/.test(token.text),
    );

    expect(unread.map(({ slug, token }) => [slug, token.raw])).toEqual([]);
  });

  it('only links to guides that exist, the settings, or the web', () => {
    const broken = tokens.flatMap(({ slug, token }) => {
      if (token.type !== 'link') return [];
      if (token.href === '/settings' || token.href.startsWith('https://')) return [];
      const [, docs, target] = token.href.split('/');
      return docs === 'docs' && guideBySlug(target) ? [] : [[slug, token.href]];
    });

    expect(broken).toEqual([]);
  });

  it.each(['sidebar', 'dashboard', 'grid', 'dialog', 'Streamlit', 'hover a slice'])(
    'no longer talks about the old app’s “%s”',
    (word) => {
      const mentions = GUIDES.filter((guide) =>
        guide.body.toLowerCase().includes(word.toLowerCase()),
      ).map((guide) => guide.slug);

      expect(mentions).toEqual([]);
    },
  );
});

describe('guideBySlug', () => {
  it('finds a guide', () => {
    expect(guideBySlug('payments')?.title).toBe('Payments');
  });

  it('finds nothing at an unknown slug', () => {
    expect(guideBySlug('nope')).toBeUndefined();
  });
});
