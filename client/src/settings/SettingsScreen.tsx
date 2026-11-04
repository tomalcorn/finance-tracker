import { useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { useAuth } from '@/auth/AuthProvider';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ListRow } from '@/components/ListRow';
import { Screen } from '@/components/Screen';
import { Toast, type ToastMessage } from '@/components/Toast';
import { useRepositories, useRows } from '@/hooks/repositories';
import { IncomeMonthSetting } from '@/settings/IncomeMonthSetting';
import { HalfThemeProvider } from '@/theme/theme';

/** The preferences behind how each half adds things up, the account, and logging out. */
export function SettingsScreen() {
  const { state, logout } = useAuth();
  const router = useRouter();
  const jointAccounts = useRows(useRepositories().jointAccounts());
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const dismissToast = useCallback(() => setToast(null), []);
  const notify = useCallback((text: string) => {
    setToast((current) => ({ id: (current?.id ?? 0) + 1, text }));
  }, []);
  const user = state.status === 'signedIn' ? state.user : null;
  const jointAccount = jointAccounts.data?.[0];

  return (
    <View style={styles.fill}>
      <Screen title="Settings">
        <Card title="Personal">
          <IncomeMonthSetting ownership="personal" onSaved={notify} />
        </Card>

        <HalfThemeProvider half="joint">
          <Card title="Joint">
            {jointAccounts.error ? (
              <AppText tone="negative">
                Could not load your joint account: {jointAccounts.error.message}
              </AppText>
            ) : jointAccounts.isPending ? (
              <AppText tone="muted">Loading…</AppText>
            ) : jointAccount ? (
              <>
                <AppText tone="muted">Shared account · {jointAccount.name}</AppText>
                <IncomeMonthSetting ownership="joint" onSaved={notify} />
              </>
            ) : (
              <>
                <AppText tone="muted">
                  You don’t have a joint account yet. Once you’re a member of one, its settings
                  appear here.
                </AppText>
                <Button
                  title="Read the Joint Accounts guide"
                  variant="plain"
                  onPress={() => router.push('/docs/joint_accounts')}
                />
              </>
            )}
          </Card>
        </HalfThemeProvider>

        <Card title="Account" list>
          <ListRow title="Signed in as" subtitle={user?.email ?? user?.sub} />
        </Card>
        <Card title="More" list>
          <ListRow title="Docs" onPress={() => router.push('/docs')} />
          <ListRow
            title="Design"
            subtitle="The theme and shared components"
            onPress={() => router.push('/design')}
          />
        </Card>
        <Button title="Log out" variant="destructive" onPress={logout} />
      </Screen>
      <Toast toast={toast} onDismiss={dismissToast} />
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
});
