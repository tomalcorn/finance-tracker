import { Redirect, useLocalSearchParams } from 'expo-router';
import { Button, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthProvider';
import { CenteredStatus } from '@/components/CenteredStatus';

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
        <View style={styles.container}>
          <Text role="heading" style={styles.title}>
            Finance Tracker
          </Text>
          {state.error ? <Text style={styles.error}>{state.error}</Text> : null}
          <Button title="Log in" onPress={() => login(returnTo ?? '/')} />
        </View>
      );
  }
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 16, padding: 24 },
  title: { fontSize: 28, fontWeight: '600' },
  error: { color: '#b00020', textAlign: 'center' },
});
