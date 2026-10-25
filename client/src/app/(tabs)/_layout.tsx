import { Redirect, Tabs, usePathname } from 'expo-router';
import type { ReactNode } from 'react';

import { useAuth } from '@/auth/AuthProvider';
import { CenteredStatus } from '@/components/CenteredStatus';
import { DataProvider } from '@/composition/DataProvider';

const noTabBar = () => null;

export default function TabsLayout() {
  const { state } = useAuth();
  const signedIn = state.status === 'signedIn';

  return (
    <Tabs
      screenLayout={({ children }) => <SignedInOnly>{children}</SignedInOnly>}
      screenOptions={{ headerShown: signedIn }}
      tabBar={signedIn ? undefined : noTabBar}
    >
      <Tabs.Screen name="index" options={{ title: 'Quick Expenses' }} />
      <Tabs.Screen name="personal" options={{ title: 'Personal' }} />
      <Tabs.Screen name="joint" options={{ title: 'Joint' }} />
      <Tabs.Screen name="settings" options={{ title: 'Settings' }} />
    </Tabs>
  );
}

/** A tab's screen once signed in; until then a status, or a redirect to sign-in. */
function SignedInOnly({ children }: { children: ReactNode }) {
  const { state } = useAuth();
  const pathname = usePathname();

  switch (state.status) {
    case 'loading':
      return <CenteredStatus />;
    case 'unavailable':
      return <CenteredStatus message={state.error} />;
    case 'signedOut':
      return <Redirect href={{ pathname: '/sign-in', params: { returnTo: pathname } }} />;
    case 'signedIn':
      return <DataProvider userId={state.user.sub}>{children}</DataProvider>;
  }
}
