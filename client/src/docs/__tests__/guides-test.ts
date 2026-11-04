import { GUIDES, guideBySlug } from '@/docs/guides';
import { parseMarkdown, type Block, type Inline } from '@/docs/parseMarkdown';

function inlinesOf(block: Block): Inline[] {
  switch (block.kind) {
    case 'paragraph':
    case 'quote':
      return block.inlines;
    case 'list':
      return block.items.flat();
    case 'table':
      return [...block.header, ...block.rows.flat()].flat();
    case 'heading':
      return [];
  }
}

const guideInlines = GUIDES.flatMap((guide) =>
  parseMarkdown(guide.body)
    .flatMap(inlinesOf)
    .map((inline) => ({ slug: guide.slug, inline })),
);

const links = guideInlines.flatMap(({ slug, inline }) =>
  inline.kind === 'link' ? [{ slug, href: inline.href }] : [],
);

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

  it('leaves no markdown unread', () => {
    const unread = guideInlines.filter(
      ({ inline }) => inline.kind === 'text' && /\*\*|\]\(|^#|^\|/.test(inline.text),
    );

    expect(unread).toEqual([]);
  });

  it('only links to guides that exist, the settings, or the web', () => {
    const broken = links.filter(({ href }) => {
      if (href === '/settings' || href.startsWith('https://')) return false;
      const [, docs, slug] = href.split('/');
      return docs !== 'docs' || !guideBySlug(slug);
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
