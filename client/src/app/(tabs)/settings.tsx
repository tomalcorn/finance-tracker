import { useRouter } from 'expo-router';
import { useState } from 'react';

import { useAuth } from '@/auth/AuthProvider';
import { Amount } from '@/components/Amount';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ListRow } from '@/components/ListRow';
import { Screen } from '@/components/Screen';
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
    <>
      <Card title="Data probe" list>
        <ListRow title={`Quick buttons: ${countOf(rows)}`} />
        {probeRows.map((row) => (
          <ListRow key={row.id} title={row.name} trailing={<Amount value={row.expense ?? 0} />} />
        ))}
      </Card>
      <Button title="Add a probe button" variant="secondary" onPress={add} />
      <Button
        title="Add £1 to the first"
        variant="secondary"
        onPress={edit}
        disabled={probeRows.length === 0}
      />
      <Button
        title="Delete probe buttons"
        variant="destructive"
        onPress={remove}
        disabled={probeRows.length === 0}
      />
      {error ? <AppText tone="negative">{error}</AppText> : null}
    </>
  );
}

export default function SettingsScreen() {
  const { state, logout } = useAuth();
  const router = useRouter();
  const payments = useRows(useRepositories().payments('personal'));
  const user = state.status === 'signedIn' ? state.user : null;

  return (
    <Screen>
      <AppText tone="muted">Coming in #302.</AppText>
      <Card title="Account" list>
        <ListRow title="Signed in as" subtitle={user?.email ?? user?.sub} />
        <ListRow
          title="Personal payments visible"
          trailing={<AppText tone="muted">{countOf(payments)}</AppText>}
        />
      </Card>
      <QuickButtonProbe />
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
  );
}
