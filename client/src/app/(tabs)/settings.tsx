import { Link } from 'expo-router';
import { useEffect, useState } from 'react';
import { Button, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthProvider';
import { useServices } from '@/composition/ServicesProvider';

/** How many payments the signed-in user can read: a check that RLS sees them. */
function useVisiblePaymentCount(): string {
  const { supabase } = useServices();
  const [count, setCount] = useState('…');

  useEffect(() => {
    let cancelled = false;
    supabase
      .from('payments')
      .select('*', { count: 'exact', head: true })
      .then(({ count, error }) => {
        if (!cancelled) setCount(error ? `error: ${error.message}` : String(count ?? 0));
      });
    return () => {
      cancelled = true;
    };
  }, [supabase]);

  return count;
}

export default function SettingsScreen() {
  const { state, logout } = useAuth();
  const paymentCount = useVisiblePaymentCount();
  const user = state.status === 'signedIn' ? state.user : null;

  return (
    <View style={styles.container}>
      <Text role="heading" style={styles.title}>
        Settings
      </Text>
      <Text>Coming in #302.</Text>
      <Text>Signed in as {user?.email ?? user?.sub}</Text>
      <Text>Payments visible: {paymentCount}</Text>
      <Button title="Log out" onPress={logout} />
      <Link href="/docs" style={styles.link}>
        Docs
      </Link>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, padding: 24 },
  title: { fontSize: 24, fontWeight: '600' },
  link: { padding: 16 },
});
