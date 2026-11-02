import type { PaymentView } from '@/domain/readModels';

/** Something a search can filter on with `@key:value`. */
export type SearchField = {
  key: string;
  /** What the field is, shown beside it when prompting. */
  hint: string;
  /** The values to choose from. */
  options: readonly string[];
  /** A payment's value for this field, or null when it has none. */
  valueOf: (payment: PaymentView) => string | null;
};

/** What a search asks for: text to look for, and the fields a payment must match. */
export type ParsedSearch = {
  text: string;
  filters: readonly { field: SearchField; value: string }[];
};

/** A way to carry on typing: what to show, and the whole search it leaves in the box. */
export type SearchSuggestion = { label: string; hint?: string; query: string };

const MAX_SUGGESTIONS = 12;

/** The filters offered on payments, given the names to choose from. */
export function paymentSearchFields(choices: {
  names: readonly string[];
  bankAccounts: readonly string[];
  categories: readonly string[];
  incomeSources: readonly string[];
  /** The name of a bank account, category or income source, by id. */
  labelOf: (id: string) => string | undefined;
}): SearchField[] {
  const label = (id: string | null) => (id ? (choices.labelOf(id) ?? null) : null);
  return [
    {
      key: 'account',
      hint: 'Bank account',
      options: choices.bankAccounts,
      valueOf: (payment) => label(payment.bank_account_id),
    },
    {
      key: 'category',
      hint: 'Budget tracker or category',
      options: choices.categories,
      valueOf: (payment) => label(payment.category_id),
    },
    {
      key: 'source',
      hint: 'Income source',
      options: choices.incomeSources,
      valueOf: (payment) => label(payment.income_source_id),
    },
    {
      key: 'name',
      hint: 'The name alone',
      options: choices.names,
      valueOf: (payment) => payment.name,
    },
    {
      key: 'type',
      hint: 'Money out or in',
      options: ['out', 'in'],
      valueOf: (payment) => (payment.payment_type === 'income' ? 'in' : 'out'),
    },
    {
      key: 'checked',
      hint: 'Ticked or not',
      options: ['yes', 'no'],
      valueOf: (payment) => (payment.checked ? 'yes' : 'no'),
    },
  ];
}

type Token = {
  /** Where the `@` is. */
  start: number;
  /** Where the text after the token begins. */
  end: number;
  key: string;
  hasColon: boolean;
};

/** The `@key` and `@key:` tokens in a search. An `@` inside a word isn't one. */
function tokensIn(query: string): Token[] {
  return [...query.matchAll(/(^|\s)@([a-z]*)(:?)/gi)].map((match) => {
    const start = match.index + (match[1]?.length ?? 0);
    return {
      start,
      end: match.index + match[0].length,
      key: (match[2] ?? '').toLowerCase(),
      hasColon: match[3] === ':',
    };
  });
}

/**
 * Split what follows `@key:` into the value and the search text after it: the most words that
 * still name part of an option, so a value can hold spaces without quotes. A field's text with no
 * such option keeps only its first word as the value.
 */
function splitValue(text: string, options: readonly string[]): { value: string; rest: string } {
  const words = text.trim().split(/\s+/).filter(Boolean);
  const lowered = options.map((option) => option.toLowerCase());
  for (let count = words.length; count > 0; count--) {
    const value = words.slice(0, count).join(' ').toLowerCase();
    if (lowered.some((option) => option.includes(value))) {
      return { value, rest: words.slice(count).join(' ') };
    }
  }
  return { value: (words[0] ?? '').toLowerCase(), rest: words.slice(1).join(' ') };
}

/**
 * Read a search into its text and filters. A filter still being typed (`@`, `@acc`, `@account:`)
 * asks for nothing yet. An `@word` that can't become a filter is ordinary text.
 */
export function parseSearch(query: string, fields: readonly SearchField[]): ParsedSearch {
  const tokens = tokensIn(query);
  const text: string[] = [query.slice(0, tokens[0]?.start ?? query.length)];
  const filters: { field: SearchField; value: string }[] = [];

  tokens.forEach((token, index) => {
    const after = query.slice(token.end, tokens[index + 1]?.start ?? query.length);
    const field = fields.find((candidate) => candidate.key === token.key);
    if (field && token.hasColon) {
      const { value, rest } = splitValue(after, field.options);
      if (value) filters.push({ field, value });
      text.push(rest);
    } else if (!token.hasColon && fields.some((candidate) => candidate.key.startsWith(token.key))) {
      text.push(after);
    } else {
      text.push(query.slice(token.start, token.end) + after);
    }
  });

  return {
    text: text
      .map((part) => part.trim())
      .filter(Boolean)
      .join(' ')
      .toLowerCase(),
    filters,
  };
}

/**
 * Whether a payment's value satisfies a filter. A value naming an option means that option, and a
 * budget tracker's subcategories along with it; anything else is looked for inside the value.
 */
function matchesFilter(payment: PaymentView, field: SearchField, value: string): boolean {
  const actual = field.valueOf(payment)?.toLowerCase();
  if (!actual) return false;
  const named = field.options.some((option) => option.toLowerCase() === value);
  return named ? actual === value || actual.startsWith(`${value} - `) : actual.includes(value);
}

/**
 * Whether a payment is one a search asks for: every filter matches, and the text is in its name or
 * the words describing it.
 */
export function matchesSearch(
  payment: PaymentView,
  search: ParsedSearch,
  describe: (payment: PaymentView) => string,
): boolean {
  const { text, filters } = search;
  return (
    filters.every(({ field, value }) => matchesFilter(payment, field, value)) &&
    (text === '' || `${payment.name} ${describe(payment)}`.toLowerCase().includes(text))
  );
}

/** What can finish the filter being typed at the end of a search: its fields, then its values. */
export function searchSuggestions(
  query: string,
  fields: readonly SearchField[],
): SearchSuggestion[] {
  const token = tokensIn(query).at(-1);
  if (!token) return [];
  const before = query.slice(0, token.start);
  const after = query.slice(token.end);

  if (!token.hasColon) {
    if (after !== '') return [];
    return fields
      .filter((field) => field.key.startsWith(token.key))
      .map((field) => ({
        label: `@${field.key}:`,
        hint: field.hint,
        query: `${before}@${field.key}:`,
      }));
  }

  const field = fields.find((candidate) => candidate.key === token.key);
  if (!field) return [];
  const typed = after.trim().toLowerCase();
  const chosen = field.options.some((option) => option.toLowerCase() === typed);
  if (chosen && /\s$/.test(after)) return [];
  const options = field.options.filter((option) => option.toLowerCase().includes(typed));
  if (chosen && options.length === 1) return [];
  return options.slice(0, MAX_SUGGESTIONS).map((option) => ({
    label: option,
    query: `${before}@${field.key}:${option} `,
  }));
}
