import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { Children, type ReactNode, useRef, useState } from 'react';
import { Platform, Pressable, StyleSheet, TextInput, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { interactiveBackground } from '@/components/interaction';
import { useAppTheme } from '@/theme/theme';
import { formatAmount, formatAmountCompact, parseAmount } from '@/theme/formatAmount';
import { RADIUS, SPACING } from '@/theme/tokens';

const PENCIL: SymbolViewProps['name'] = { ios: 'pencil', web: 'edit' };

/** Amounts longer than this many characters are set smaller, so three cards fit across a phone. */
const LONG = 7;

/** Cards in a row before the next row starts. */
const PER_ROW = 3;

type EditableFigureProps = {
  label: string;
  value: number;
  /** What is wrong with the amount as typed, or undefined when it will do. */
  validate: (text: string) => string | undefined;
  /** Save the amount; rejects with a message to show when it can't. */
  onSave: (amount: number) => Promise<void>;
  /** Under the amount, e.g. what it means. */
  caption?: string;
};

/**
 * An amount on a card that turns into its own input when tapped. Return or leaving the field
 * saves it, and Escape puts it back.
 */
export function EditableFigure({ label, value, validate, onSave, caption }: EditableFigureProps) {
  const { colors } = useAppTheme();
  const [text, setText] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<string | null>(null);
  // Escape closes the input, and losing focus as it goes must not save what it held.
  const cancelled = useRef(false);
  const editing = text !== null;
  const error = editing ? validate(text) : undefined;

  function start() {
    cancelled.current = false;
    setFailure(null);
    setText(value.toFixed(2));
  }

  async function finish() {
    if (text === null || saving || cancelled.current) return;
    const amount = parseAmount(text);
    if (error || amount === null || Number.isNaN(amount)) return;
    if (amount === value) {
      setText(null);
      return;
    }
    setSaving(true);
    try {
      await onSave(amount);
      setText(null);
    } catch (failed) {
      setFailure(failed instanceof Error ? failed.message : String(failed));
    } finally {
      setSaving(false);
    }
  }

  const message = error ?? failure ?? caption;
  const shown = formatAmountCompact(value);

  return (
    <View style={styles.cell}>
      {editing ? (
        <View
          style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.accent }]}
        >
          <AppText variant="caption" tone="muted">
            {label}
          </AppText>
          <TextInput
            aria-label={label}
            aria-invalid={error ? true : undefined}
            value={text}
            onChangeText={setText}
            onSubmitEditing={() => void finish()}
            onBlur={() => void finish()}
            onKeyPress={(event) => {
              if (event.nativeEvent.key !== 'Escape') return;
              cancelled.current = true;
              setText(null);
            }}
            inputMode="decimal"
            autoFocus
            selectTextOnFocus
            editable={!saving}
            style={[
              styles.amount,
              styles.input,
              { color: colors.text, backgroundColor: colors.surfaceMuted },
              Platform.OS === 'web' && styles.noOutline,
            ]}
          />
          {message ? (
            <AppText
              variant="caption"
              tone={error || failure ? 'negative' : 'muted'}
              numberOfLines={2}
            >
              {message}
            </AppText>
          ) : null}
        </View>
      ) : (
        <Pressable
          role="button"
          aria-label={`${label} ${formatAmount(value)}, edit`}
          onPress={start}
          style={(state) => [
            styles.card,
            {
              backgroundColor: interactiveBackground(state, colors, colors.surface),
              borderColor: colors.border,
            },
          ]}
        >
          <View style={styles.top}>
            <AppText variant="caption" tone="muted" numberOfLines={1} style={styles.label}>
              {label}
            </AppText>
            <SymbolView name={PENCIL} size={14} tintColor={colors.accent} />
          </View>
          <AppText
            numberOfLines={1}
            style={[styles.amount, shown.length > LONG && styles.long, { color: colors.text }]}
          >
            {shown}
          </AppText>
          {message ? (
            <AppText variant="caption" tone={failure ? 'negative' : 'muted'} numberOfLines={2}>
              {message}
            </AppText>
          ) : null}
        </Pressable>
      )}
    </View>
  );
}

/** Figure cards in rows of up to three, each row's cards stretched to fill it. */
export function FigureCards({ children }: { children: ReactNode }) {
  const cards = Children.toArray(children);
  const rows: ReactNode[][] = [];
  for (let start = 0; start < cards.length; start += PER_ROW) {
    rows.push(cards.slice(start, start + PER_ROW));
  }
  return (
    <View style={styles.rows}>
      {rows.map((row, index) => (
        <View key={index} style={styles.row}>
          {row}
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  rows: { gap: SPACING.md },
  row: { flexDirection: 'row', gap: SPACING.md },
  cell: { flex: 1 },
  card: {
    flex: 1,
    minHeight: 92,
    gap: SPACING.xs,
    paddingVertical: SPACING.md,
    paddingHorizontal: SPACING.md - 2,
    borderRadius: RADIUS.lg,
    borderWidth: StyleSheet.hairlineWidth,
  },
  top: { flexDirection: 'row', alignItems: 'center', gap: SPACING.xs },
  label: { flex: 1 },
  amount: { fontSize: 18, lineHeight: 24, fontWeight: '600', fontVariant: ['tabular-nums'] },
  long: { fontSize: 15 },
  input: {
    minHeight: 32,
    minWidth: 0,
    paddingHorizontal: SPACING.xs,
    borderRadius: RADIUS.sm,
    fontVariant: ['tabular-nums'],
  },
  noOutline: { outlineStyle: 'none' } as object,
});
