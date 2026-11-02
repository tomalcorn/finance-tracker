import { Pressable, StyleSheet } from 'react-native';

import { AppText } from '@/components/AppText';
import { Card } from '@/components/Card';
import { interactiveBackground } from '@/components/interaction';
import type { SearchSuggestion } from '@/payments/paymentSearch';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

type SearchSuggestionsProps = {
  suggestions: readonly SearchSuggestion[];
  onChoose: (suggestion: SearchSuggestion) => void;
};

/** The ways to finish the filter being typed, shown under the search box while there are any. */
export function SearchSuggestions({ suggestions, onChoose }: SearchSuggestionsProps) {
  const { colors } = useAppTheme();
  if (suggestions.length === 0) return null;

  return (
    <Card list>
      {suggestions.map((suggestion) => (
        <Pressable
          key={suggestion.query}
          role="button"
          aria-label={suggestion.label}
          onPress={() => onChoose(suggestion)}
          style={(state) => [styles.row, { backgroundColor: interactiveBackground(state, colors) }]}
        >
          <AppText numberOfLines={1} style={styles.label}>
            {suggestion.label}
          </AppText>
          {suggestion.hint ? (
            <AppText variant="caption" tone="muted" numberOfLines={1}>
              {suggestion.hint}
            </AppText>
          ) : null}
        </Pressable>
      ))}
    </Card>
  );
}

const styles = StyleSheet.create({
  row: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.sm,
  },
  label: { flex: 1 },
});
