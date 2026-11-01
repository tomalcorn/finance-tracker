import { useRouter } from 'expo-router';

import { useAuth } from '@/auth/AuthProvider';
import { AppText } from '@/components/AppText';
import { Button } from '@/components/Button';
import { Card } from '@/components/Card';
import { ListRow } from '@/components/ListRow';
import { Screen } from '@/components/Screen';
import { useRepositories, useRows } from '@/hooks/repositories';

function countOf(result: { data?: unknown[]; error: Error | null }): string {
  if (result.error) return `error: ${result.error.message}`;
  return result.data ? String(result.data.length) : '…';
}

export default function SettingsScreen() {
  const { state, logout } = useAuth();
  const router = useRouter();
  const payments = useRows(useRepositories().payments('personal'));
  const user = state.status === 'signedIn' ? state.user : null;

  return (
    <Screen title="Settings">
      <AppText tone="muted">Coming in #302.</AppText>
      <Card title="Account" list>
        <ListRow title="Signed in as" subtitle={user?.email ?? user?.sub} />
        <ListRow
          title="Personal payments visible"
          trailing={<AppText tone="muted">{countOf(payments)}</AppText>}
        />
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
  );
}
