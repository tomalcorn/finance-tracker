import { Tabs } from 'expo-router';

export default function TabsLayout() {
  return (
    <Tabs>
      <Tabs.Screen name="index" options={{ title: 'Quick Expenses' }} />
      <Tabs.Screen name="personal" options={{ title: 'Personal' }} />
      <Tabs.Screen name="joint" options={{ title: 'Joint' }} />
      <Tabs.Screen name="settings" options={{ title: 'Settings' }} />
    </Tabs>
  );
}
