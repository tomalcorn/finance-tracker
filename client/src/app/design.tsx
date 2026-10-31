import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Amount } from '@/components/Amount';
import { AppIcon } from '@/components/AppIcon';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { GlassTabBar, type GlassTabItem } from '@/components/GlassTabBar';
import { ListRow } from '@/components/ListRow';
import { ProgressBar } from '@/components/ProgressBar';
import { Screen } from '@/components/Screen';
import { Sheet } from '@/components/Sheet';
import { TextField } from '@/components/TextField';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING, type Palette } from '@/theme/tokens';

const SAMPLE_TABS = [
  { key: 'quick', label: 'Quick', icon: { ios: 'bolt.fill', web: 'bolt' } },
  { key: 'personal', label: 'Personal', icon: { ios: 'person.fill', web: 'person' } },
  { key: 'joint', label: 'Joint', icon: { ios: 'person.2.fill', web: 'group' } },
  { key: 'settings', label: 'Settings', icon: { ios: 'gearshape.fill', web: 'settings' } },
] as const satisfies readonly GlassTabItem[];

type SamplePayment = { id: string; date: string; name: string; category: string; amount: number };

const SAMPLE_PAYMENTS: SamplePayment[] = [
  { id: '1', date: '28 Oct', name: 'Tesco', category: 'Groceries', amount: -46.2 },
  { id: '2', date: '25 Oct', name: 'Salary', category: 'Income', amount: 2450 },
  { id: '3', date: '24 Oct', name: 'Trainline', category: 'Transport', amount: -38.5 },
  { id: '4', date: '21 Oct', name: 'Netflix', category: 'Subscriptions', amount: -10.99 },
  { id: '5', date: '19 Oct', name: 'Dishoom', category: 'Eating out', amount: -64 },
];

const NEW_PAYMENT: SamplePayment = { id: '', date: '', name: '', category: '', amount: 0 };

/** A gallery of the theme and every shared component, with sample data, for reviewing the design. */
export default function DesignScreen() {
  const { colors } = useAppTheme();
  const [amount, setAmount] = useState('12.50');
  const [tab, setTab] = useState<string>(SAMPLE_TABS[0].key);
  const [editing, setEditing] = useState<SamplePayment | null>(null);

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

      <Card title="App icon">
        <View style={styles.icons}>
          <AppIcon size={64} />
          <AppIcon size={40} />
          <AppIcon size={24} />
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

      <Card title="Sheet">
        <AppText variant="caption" tone="muted">
          Tap a payment to edit it, or add a new one. On a phone the sheet slides up; on a wide
          window it opens as a dialog.
        </AppText>
        <Card list>
          {SAMPLE_PAYMENTS.map((payment) => (
            <ListRow
              key={payment.id}
              title={payment.name}
              subtitle={`${payment.category} · ${payment.date}`}
              trailing={<Amount value={payment.amount} signed />}
              onPress={() => setEditing(payment)}
            />
          ))}
        </Card>
        <Button title="Add a payment" variant="secondary" onPress={() => setEditing(NEW_PAYMENT)} />
      </Card>

      <Sheet
        visible={editing !== null}
        onClose={() => setEditing(null)}
        title={editing?.id ? `Edit ${editing.name}` : 'Add a payment'}
        footer={
          <>
            <Button title="Save" onPress={() => setEditing(null)} />
            <Button title="Cancel" variant="plain" onPress={() => setEditing(null)} />
          </>
        }
      >
        <TextField label="Name" defaultValue={editing?.name} placeholder="e.g. Coffee" />
        <TextField
          label="Amount"
          defaultValue={editing?.id ? Math.abs(editing.amount).toFixed(2) : ''}
          inputMode="decimal"
          placeholder="0.00"
        />
        <TextField label="Category" defaultValue={editing?.category} />
      </Sheet>
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
  icons: { flexDirection: 'row', alignItems: 'flex-end', gap: SPACING.lg },
  swatches: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACING.md },
  swatch: { width: 88, gap: SPACING.xs },
  chip: { height: 40, borderRadius: RADIUS.sm, borderWidth: StyleSheet.hairlineWidth },
  budget: { gap: SPACING.sm },
  budgetHeader: { flexDirection: 'row', justifyContent: 'space-between' },
});
