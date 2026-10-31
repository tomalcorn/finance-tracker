import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { GlassTabBar, type GlassTabItem } from '@/components/GlassTabBar';
import { ListRow } from '@/components/ListRow';
import { ProgressBar } from '@/components/ProgressBar';
import { Screen } from '@/components/Screen';
import { TextField } from '@/components/TextField';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING, type Palette } from '@/theme/tokens';

const SAMPLE_TABS = [
  { key: 'quick', label: 'Quick', icon: { ios: 'bolt.fill', web: 'bolt' } },
  { key: 'personal', label: 'Personal', icon: { ios: 'person.fill', web: 'person' } },
  { key: 'joint', label: 'Joint', icon: { ios: 'person.2.fill', web: 'group' } },
  { key: 'settings', label: 'Settings', icon: { ios: 'gearshape.fill', web: 'settings' } },
] as const satisfies readonly GlassTabItem[];

/** A gallery of the theme and every shared component, with sample data, for reviewing the design. */
export default function DesignScreen() {
  const { colors } = useAppTheme();
  const [amount, setAmount] = useState('12.50');
  const [tab, setTab] = useState<string>(SAMPLE_TABS[0].key);

  return (
    <Screen title="Design" back>
      <AppText tone="muted">
        The theme and shared components, with sample data. Switch the device to dark mode to see the
        dark palette.
      </AppText>

      <Card title="Tab bar">
        <View style={[styles.tabStage, { backgroundColor: colors.background }]}>
          <Card list>
            <ListRow
              title="Coffee"
              subtitle="Pret · Today"
              trailing={<Amount value={-3.4} signed />}
            />
            <ListRow
              title="Rent"
              subtitle="Joint · 1 Nov"
              trailing={<Amount value={-950} signed />}
            />
            <ListRow
              title="Refund"
              subtitle="Amazon · 30 Oct"
              trailing={<Amount value={24.99} signed />}
            />
          </Card>
          <GlassTabBar items={SAMPLE_TABS} selectedKey={tab} onSelect={setTab} />
        </View>
      </Card>

      <Card title="Colours">
        <View style={styles.swatches}>
          {(Object.keys(colors) as (keyof Palette)[]).map((name) => (
            <View key={name} style={styles.swatch}>
              <View
                style={[styles.chip, { backgroundColor: colors[name], borderColor: colors.border }]}
              />
              <AppText variant="caption" tone="muted">
                {name}
              </AppText>
            </View>
          ))}
        </View>
      </Card>

      <Card title="Type">
        <AppText variant="title">Title</AppText>
        <AppText variant="heading">Heading</AppText>
        <AppText>Body text for sentences and row titles.</AppText>
        <AppText variant="label">Label</AppText>
        <AppText variant="caption" tone="muted">
          Caption, for supporting detail
        </AppText>
      </Card>

      <Card title="This month" list>
        <ListRow
          title="Groceries"
          subtitle="Tesco · 28 Oct"
          trailing={<Amount value={-46.2} signed />}
        />
        <ListRow
          title="Salary"
          subtitle="Income · 25 Oct"
          trailing={<Amount value={2450} signed />}
        />
        <ListRow
          title="Netflix"
          subtitle="Subscription · 21 Oct"
          trailing={<Amount value={-10.99} signed />}
          onPress={() => {}}
        />
      </Card>

      <Card title="Budgets">
        <View style={styles.budget}>
          <View style={styles.budgetHeader}>
            <AppText variant="label">Eating out</AppText>
            <AppText variant="caption" tone="muted">
              £64 of £120
            </AppText>
          </View>
          <ProgressBar progress={64 / 120} />
        </View>
        <View style={styles.budget}>
          <View style={styles.budgetHeader}>
            <AppText variant="label">Transport</AppText>
            <AppText variant="caption" tone="muted">
              £92 of £100
            </AppText>
          </View>
          <ProgressBar progress={0.92} warn />
        </View>
      </Card>

      <Card title="Form">
        <TextField label="Name" placeholder="e.g. Coffee" />
        <TextField
          label="Amount"
          value={amount}
          onChangeText={setAmount}
          inputMode="decimal"
          error={Number.isNaN(Number(amount)) ? 'Enter an amount in pounds.' : undefined}
        />
        <Button title="Save" onPress={() => {}} />
        <Button title="Cancel" variant="secondary" onPress={() => {}} />
        <Button title="Not now" variant="plain" onPress={() => {}} />
        <Button title="Delete" variant="destructive" onPress={() => {}} />
        <Button title="Disabled" onPress={() => {}} disabled />
      </Card>
    </Screen>
  );
}

const styles = StyleSheet.create({
  tabStage: {
    height: 200,
    borderRadius: RADIUS.md,
    overflow: 'hidden',
    padding: SPACING.md,
  },
  swatches: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.md },
  swatch: { width: 88, gap: SPACING.xs },
  chip: { height: 40, borderRadius: RADIUS.sm, borderWidth: StyleSheet.hairlineWidth },
  budget: { gap: SPACING.sm },
  budgetHeader: { flexDirection: 'row', justifyContent: 'space-between' },
});
