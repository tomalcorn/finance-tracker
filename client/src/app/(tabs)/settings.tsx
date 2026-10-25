import { Link } from 'expo-router';
import { useState } from 'react';
import { Button, StyleSheet, Text, View } from 'react-native';

import { useAuth } from '@/auth/AuthProvider';
import { useRepositories, useRows } from '@/hooks/repositories';

/** The start of the name of every quick button created by the probe, so that it deletes only those. */
const PROBE_PREFIX = '[probe] ';

function countOf(result: { data?: unknown[]; error: Error | null }): string {
  if (result.error) return `error: ${result.error.message}`;
  return result.data ? String(result.data.length) : '…';
}

/**
 * Exercises the quick-button repository end to end: create, read, edit and
 * delete, touching only buttons created by the probe. Temporary until #295.
 */
function QuickButtonProbe() {
  const quickButtons = useRepositories().quickButtons('personal');
  const rows = useRows(quickButtons);
  const [error, setError] = useState<string | null>(null);
  const probeRows = (rows.data ?? []).filter((row) => row.name.startsWith(PROBE_PREFIX));

  async function run(action: () => Promise<void>) {
    setError(null);
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    }
  }

  const add = () =>
    run(async () => {
      const name = `${PROBE_PREFIX}${new Date().toISOString()}`;
      await quickButtons.save(await quickButtons.build([{ name, mode: 'prompt', expense: 1.5 }]));
    });

  const edit = () =>
    run(async () => {
      const [first] = probeRows;
      if (!first) return;
      await quickButtons.save(
        await quickButtons.build([{ ...first, expense: (first.expense ?? 0) + 1 }]),
      );
    });

  const remove = () => run(() => quickButtons.delete(probeRows.map((row) => row.id)));

  return (
    <View style={styles.probe}>
      <Text>Quick buttons: {countOf(rows)}</Text>
      {probeRows.map((row) => (
        <Text key={row.id}>
          {row.name} · £{row.expense}
        </Text>
      ))}
      <Button title="Add a probe button" onPress={add} />
      <Button title="Add £1 to the first" onPress={edit} disabled={probeRows.length === 0} />
      <Button title="Delete probe buttons" onPress={remove} disabled={probeRows.length === 0} />
      {error ? <Text style={styles.error}>{error}</Text> : null}
    </View>
  );
}

export default function SettingsScreen() {
  const { state, logout } = useAuth();
  const payments = useRows(useRepositories().payments('personal'));
  const user = state.status === 'signedIn' ? state.user : null;

  return (
    <View style={styles.container}>
      <Text role="heading" style={styles.title}>
        Settings
      </Text>
      <Text>Coming in #302.</Text>
      <Text>Signed in as {user?.email ?? user?.sub}</Text>
      <Text>Personal payments visible: {countOf(payments)}</Text>
      <QuickButtonProbe />
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
  probe: { alignItems: 'center', gap: 8 },
  error: { color: '#b00020', textAlign: 'center' },
  link: { padding: 16 },
});
