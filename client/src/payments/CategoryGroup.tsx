import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { Pressable, StyleSheet, View } from 'react-native';

import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { interactiveBackground } from '@/components/interaction';
import { ProgressBar } from '@/components/ProgressBar';
import type { PaymentView } from '@/domain/readModels';
import { PaymentRow } from '@/payments/PaymentRow';
import type { CategorySpend } from '@/payments/paymentList';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

const OPEN: SymbolViewProps['name'] = { ios: 'chevron.up', web: 'expand_less' };
const CLOSED: SymbolViewProps['name'] = { ios: 'chevron.down', web: 'expand_more' };

type CategoryGroupProps = {
  group: CategorySpend;
  label: string;
  /** Everything spent across the groups, for this one's share. */
  spent: number;
  expanded: boolean;
  onToggle: () => void;
  /** Under each payment's name, e.g. its date and account. */
  describe: (payment: PaymentView) => string;
  onOpenPayment: (payment: PaymentView) => void;
  onToggleChecked: (payment: PaymentView) => void;
};

/**
 * One category's spending: its total and share of everything spent, expanding to the payments
 * behind it. Use inside `<Card list>`.
 */
export function CategoryGroup({
  group,
  label,
  spent,
  expanded,
  onToggle,
  describe,
  onOpenPayment,
  onToggleChecked,
}: CategoryGroupProps) {
  const { colors } = useAppTheme();
  const share = spent > 0 ? group.total / spent : 0;
  const count = group.payments.length;

  return (
    <View>
      <Pressable
        role="button"
        aria-label={label}
        aria-expanded={expanded}
        onPress={onToggle}
        style={(state) => [
          styles.header,
          { backgroundColor: interactiveBackground(state, colors) },
        ]}
      >
        <View style={styles.body}>
          <View style={styles.line}>
            <AppText numberOfLines={1} style={styles.name}>
              {label}
            </AppText>
            <Amount value={group.total} />
          </View>
          <ProgressBar progress={share} />
          <AppText variant="caption" tone="muted">
            {count} {count === 1 ? 'payment' : 'payments'} · {Math.round(share * 100)}% of spending
          </AppText>
        </View>
        <SymbolView name={expanded ? OPEN : CLOSED} size={20} tintColor={colors.textMuted} />
      </Pressable>
      {expanded
        ? group.payments.map((payment) => (
            <View key={payment.id} style={[styles.payment, { borderTopColor: colors.border }]}>
              <PaymentRow
                payment={payment}
                subtitle={describe(payment)}
                onPress={() => onOpenPayment(payment)}
                onToggleChecked={() => onToggleChecked(payment)}
              />
            </View>
          ))
        : null}
    </View>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
  },
  body: { flex: 1, gap: SPACING.xs },
  line: { flexDirection: 'row', alignItems: 'center', gap: SPACING.md },
  name: { flex: 1 },
  payment: { borderTopWidth: StyleSheet.hairlineWidth },
});
