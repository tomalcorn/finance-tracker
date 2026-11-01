import { useId, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

/** One choice in a `SelectField`. */
export type SelectOption = { value: string; label: string };

type SelectFieldProps = {
  label: string;
  value: string | null;
  options: readonly SelectOption[];
  onChange: (value: string | null) => void;
  /** Offer a choice of nothing, labelled this, e.g. "None". Without it the field can't be cleared. */
  noneLabel?: string;
  /** Shown when nothing is chosen and there is no `noneLabel`. */
  placeholder?: string;
  /** Shown under the field, which is then outlined in the negative colour. */
  error?: string;
};

/**
 * A labelled choice from a short list. It opens in place rather than over the screen, so it works
 * inside a `Sheet`.
 */
export function SelectField({
  label,
  value,
  options,
  onChange,
  noneLabel,
  placeholder = 'Choose…',
  error,
}: SelectFieldProps) {
  const { colors } = useAppTheme();
  const id = useId();
  const [open, setOpen] = useState(false);
  const choices = noneLabel ? [{ value: '', label: noneLabel }, ...options] : options;
  const selected = options.find((option) => option.value === value);
  const shown = selected?.label ?? noneLabel ?? placeholder;

  function choose(choice: string) {
    onChange(choice === '' ? null : choice);
    setOpen(false);
  }

  return (
    <View style={styles.field}>
      <AppText variant="label" nativeID={id}>
        {label}
      </AppText>
      <View
        style={[
          styles.box,
          {
            backgroundColor: colors.surfaceMuted,
            borderColor: error ? colors.negative : 'transparent',
          },
        ]}
      >
        <Pressable
          role="button"
          aria-labelledby={id}
          aria-expanded={open}
          aria-invalid={error ? true : undefined}
          onPress={() => setOpen(!open)}
          style={styles.current}
        >
          <AppText tone={selected ? 'default' : 'muted'} numberOfLines={1} style={styles.text}>
            {shown}
          </AppText>
          <AppText tone="muted">{open ? '▴' : '▾'}</AppText>
        </Pressable>
        {open
          ? choices.map((choice) => {
              const checked = choice.value === (value ?? '');
              return (
                <Pressable
                  key={choice.value}
                  role="radio"
                  aria-checked={checked}
                  onPress={() => choose(choice.value)}
                  style={({ pressed }) => [
                    styles.choice,
                    { borderTopColor: colors.border },
                    pressed && { backgroundColor: colors.border },
                  ]}
                >
                  <AppText numberOfLines={1} style={styles.text}>
                    {choice.label}
                  </AppText>
                  {checked ? <AppText tone="accent">✓</AppText> : null}
                </Pressable>
              );
            })
          : null}
      </View>
      {error ? (
        <AppText variant="caption" tone="negative">
          {error}
        </AppText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: SPACING.xs },
  box: { borderRadius: RADIUS.md, borderWidth: 1.5, overflow: 'hidden' },
  current: {
    minHeight: 41,
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingHorizontal: SPACING.md,
  },
  choice: {
    minHeight: 44,
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingHorizontal: SPACING.md,
    borderTopWidth: StyleSheet.hairlineWidth,
  },
  text: { flex: 1 },
});
