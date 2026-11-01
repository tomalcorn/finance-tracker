import { Redirect, useLocalSearchParams } from 'expo-router';
import { StyleSheet, View } from 'react-native';

import { useAuth } from '@/auth/AuthProvider';
import { AppIcon } from '@/components/AppIcon';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { CenteredStatus } from '@/components/CenteredStatus';
import { Screen } from '@/components/Screen';
import { SPACING } from '@/theme/tokens';

export default function SignInScreen() {
  const { state, login } = useAuth();
  const { returnTo } = useLocalSearchParams<{ returnTo?: string }>();

  switch (state.status) {
    case 'loading':
      return <CenteredStatus />;
    case 'unavailable':
      return <CenteredStatus message={state.error} />;
    case 'signedIn':
      return <Redirect href="/" />;
    case 'signedOut':
      return (
        <Screen centred>
          <View style={styles.brand}>
            <View style={styles.icon}>
              <AppIcon size={64} />
            </View>
            <AppText variant="title">Finance Tracker</AppText>
            <AppText tone="muted">Budgets, bills and savings in one place.</AppText>
          </View>
          {state.error ? (
            <AppText tone="negative" style={styles.centre}>
              {state.error}
            </AppText>
          ) : null}
          <Button title="Log in" onPress={() => login(returnTo ?? '/')} />
        </Screen>
      );
  }
}

const styles = StyleSheet.create({
  brand: { alignItems: 'center', gap: SPACING.sm, marginBottom: SPACING.lg },
  icon: { marginBottom: SPACING.sm },
  centre: { textAlign: 'center' },
});
