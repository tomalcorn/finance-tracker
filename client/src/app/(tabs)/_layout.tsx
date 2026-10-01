import { Redirect, Tabs, usePathname } from 'expo-router';

import { useAuth } from '@/auth/AuthProvider';
import { CenteredStatus } from '@/components/CenteredStatus';

export default function TabsLayout() {
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
      return (
        <Tabs>
          <Tabs.Screen name="index" options={{ title: 'Quick Expenses' }} />
          <Tabs.Screen name="personal" options={{ title: 'Personal' }} />
          <Tabs.Screen name="joint" options={{ title: 'Joint' }} />
          <Tabs.Screen name="settings" options={{ title: 'Settings' }} />
        </Tabs>
      );
  }
}
