import { Redirect, usePathname } from 'expo-router';
import Tabs, { type BottomTabBarProps } from 'expo-router/js-tabs';
import type { ReactNode } from 'react';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAuth } from '@/auth/AuthProvider';
import { CenteredStatus } from '@/components/CenteredStatus';
import {
  GlassTabBar,
  TabBarClearanceContext,
  tabBarClearance,
  type GlassTabItem,
} from '@/components/GlassTabBar';
import { DataProvider } from '@/composition/DataProvider';

/** The tabs in order: `key` is the route name, `label` the short name under the icon. */
const TABS: readonly (GlassTabItem & { title: string })[] = [
  {
    key: 'index',
    title: 'Quick Expenses',
    label: 'Quick',
    icon: { ios: 'bolt.fill', web: 'bolt' },
  },
  {
    key: 'personal',
    title: 'Personal',
    label: 'Personal',
    icon: { ios: 'person.fill', web: 'person' },
  },
  { key: 'joint', title: 'Joint', label: 'Joint', icon: { ios: 'person.2.fill', web: 'group' } },
  {
    key: 'settings',
    title: 'Settings',
    label: 'Settings',
    icon: { ios: 'gearshape.fill', web: 'settings' },
  },
];

const noTabBar = () => null;

export default function TabsLayout() {
  const { state } = useAuth();
  const insets = useSafeAreaInsets();
  const signedIn = state.status === 'signedIn';

  return (
    <Tabs
      screenLayout={({ children }) => (
        <TabBarClearanceContext.Provider value={signedIn ? tabBarClearance(insets.bottom) : 0}>
          <SignedInOnly>{children}</SignedInOnly>
        </TabBarClearanceContext.Provider>
      )}
      screenOptions={{ headerShown: false }}
      tabBar={signedIn ? TabBar : noTabBar}
    >
      {TABS.map((tab) => (
        <Tabs.Screen key={tab.key} name={tab.key} options={{ title: tab.title }} />
      ))}
    </Tabs>
  );
}

/** The navigator's tab bar: the glass bar over the routes, pressing one as a stock tab would. */
function TabBar({ state, navigation, insets }: BottomTabBarProps) {
  const selected = state.routes[state.index];

  function select(key: string) {
    const route = state.routes.find((candidate) => candidate.name === key);
    if (!route) return;
    const event = navigation.emit({ type: 'tabPress', target: route.key, canPreventDefault: true });
    if (route.key !== selected?.key && !event.defaultPrevented) {
      navigation.navigate(route.name, route.params);
    }
  }

  return (
    <GlassTabBar
      items={TABS}
      selectedKey={selected?.name ?? ''}
      onSelect={select}
      bottomInset={insets.bottom}
    />
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
