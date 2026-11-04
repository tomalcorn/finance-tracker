import type { SymbolViewProps } from 'expo-symbols';

/** One page of the in-app docs. */
export type Guide = {
  /** Its address under `/docs`. */
  slug: string;
  title: string;
  /** Where it comes in the list of guides, lowest first. */
  order: number;
  icon: SymbolViewProps['name'];
  /** The page, in the markdown `parseMarkdown` reads. Its heading comes from `title`. */
  body: string;
};
