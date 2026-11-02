import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { interactiveBackground } from '@/components/interaction';
import type { PaymentView } from '@/domain/readModels';
import { signedAmount } from '@/payments/paymentList';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

type PaymentRowProps = {
  payment: PaymentView;
  /** Under the name, e.g. its category and bank account. */
  subtitle: string;
  /** Open the payment to edit it. */
  onPress: () => void;
  /** Tick it as checked, or untick it. */
  onToggleChecked: () => void;
};

/** One payment in a day's list: a tick for checked, its name and details, and its signed amount. */
export function PaymentRow({ payment, subtitle, onPress, onToggleChecked }: PaymentRowProps) {
  const { colors } = useAppTheme();
  // The tick and the body are separate buttons, but the row lights up as one.
  const [hovered, setHovered] = useState(false);
  const [pressed, setPressed] = useState(false);
  const highlight = {
    onHoverIn: () => setHovered(true),
    onHoverOut: () => setHovered(false),
    onPressIn: () => setPressed(true),
    onPressOut: () => setPressed(false),
  };

  return (
    <View
      style={[styles.row, { backgroundColor: interactiveBackground({ pressed, hovered }, colors) }]}
    >
      <Pressable
        {...highlight}
        role="checkbox"
        aria-checked={payment.checked}
        aria-label={`${payment.name} checked`}
        onPress={onToggleChecked}
        hitSlop={SPACING.sm}
        style={styles.tickArea}
      >
        <View
          style={[
            styles.tick,
            payment.checked
              ? { backgroundColor: colors.positive, borderColor: colors.positive }
              : { borderColor: colors.textMuted },
          ]}
        >
          {payment.checked ? (
            <AppText variant="caption" style={{ color: colors.onAccent }}>
              ✓
            </AppText>
          ) : null}
        </View>
      </Pressable>
      <Pressable
        {...highlight}
        role="button"
        aria-label={payment.name}
        onPress={onPress}
        style={styles.body}
      >
        <View style={styles.text}>
          <AppText numberOfLines={1}>{payment.name}</AppText>
          {subtitle ? (
            <AppText variant="caption" tone="muted" numberOfLines={1}>
              {subtitle}
            </AppText>
          ) : null}
        </View>
        <Amount value={signedAmount(payment)} signed />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { minHeight: 56, flexDirection: 'row', alignItems: 'stretch' },
  tickArea: {
    justifyContent: 'center',
    paddingLeft: SPACING.lg,
    paddingRight: SPACING.sm,
  },
  tick: {
    width: 22,
    height: 22,
    borderRadius: 11,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
    paddingLeft: SPACING.sm,
    paddingRight: SPACING.lg,
    paddingVertical: SPACING.md,
  },
  text: { flex: 1, gap: 2 },
});
