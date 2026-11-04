import { StyleSheet, View } from 'react-native';

import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { Card } from '@/components/Card';
import { Sparkline } from '@/components/Sparkline';
import { formatAmount } from '@/theme/formatAmount';
import { SPACING } from '@/theme/tokens';

type BankAccountTileProps = {
  name: string;
  balance: number;
  /** The balances to draw, oldest first; `null` holds their place until the payments are known. */
  trend: readonly number[] | null;
  onPress: () => void;
};

const SPARKLINE_HEIGHT = 44;

/** An account's current balance with a trend line under it, for laying out in a wrapping row. */
export function BankAccountTile({ name, balance, trend, onPress }: BankAccountTileProps) {
  return (
    <View style={styles.tile}>
      <Card label={`${name}, ${formatAmount(balance)}`} onPress={onPress}>
        <View style={styles.figures}>
          <AppText variant="label" tone="muted" numberOfLines={1}>
            {name}
          </AppText>
          <Amount value={balance} variant="heading" />
        </View>
        {trend ? (
          <Sparkline values={trend} height={SPARKLINE_HEIGHT} />
        ) : (
          <View style={styles.sparklineSpace} />
        )}
      </Card>
    </View>
  );
}

/** Fills the empty half of a row, so a tile left over on the last row is no wider than the rest. */
export function BankAccountTileSpacer() {
  return <View style={styles.tile} />;
}

const styles = StyleSheet.create({
  tile: { flexBasis: '45%', flexGrow: 1, minWidth: 0 },
  figures: { gap: SPACING.xs },
  sparklineSpace: { height: SPARKLINE_HEIGHT },
});
