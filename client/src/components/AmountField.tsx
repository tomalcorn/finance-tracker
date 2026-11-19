import { useRef } from 'react';
import { Pressable, StyleSheet, type TextInput } from 'react-native';

import { AppText } from '@/components/AppText';
import { TextField } from '@/components/TextField';
import { flipSign } from '@/theme/formatAmount';
import { useAppTheme } from '@/theme/theme';
import { RADIUS } from '@/theme/tokens';

type AmountFieldProps = {
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  error?: string;
};

/**
 * An amount in pounds, typed on the phone's number pad, with a ± button beside it to make the
 * amount negative. The number pad has no minus key on iOS, and no keyboard has both.
 */
export function AmountField({ label, value, onChangeText, error }: AmountFieldProps) {
  const { colors } = useAppTheme();
  const input = useRef<TextInput>(null);

  function flip() {
    onChangeText(flipSign(value));
    // Tapping the button takes focus from the field; give it back so the number pad stays up.
    input.current?.focus();
  }

  return (
    <TextField
      ref={input}
      label={label}
      value={value}
      onChangeText={onChangeText}
      inputMode="decimal"
      placeholder="0.00"
      error={error}
      trailing={
        <Pressable
          role="button"
          aria-label={value.trimStart().startsWith('-') ? 'Make positive' : 'Make negative'}
          onPress={flip}
          style={({ pressed }) => [
            styles.sign,
            { backgroundColor: pressed ? colors.accentSoft : colors.surfaceMuted },
          ]}
        >
          <AppText style={[styles.signText, { color: colors.accent }]}>±</AppText>
        </Pressable>
      }
    />
  );
}

const styles = StyleSheet.create({
  sign: {
    width: 44,
    minHeight: 44,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: RADIUS.md,
  },
  signText: { fontSize: 20, fontWeight: '600' },
});
