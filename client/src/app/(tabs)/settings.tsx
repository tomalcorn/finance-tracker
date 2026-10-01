import { Link } from 'expo-router';
import { View } from 'react-native';

import { PlaceholderScreen } from '@/components/PlaceholderScreen';

export default function SettingsScreen() {
  return (
    <View style={{ flex: 1 }}>
      <PlaceholderScreen title="Settings" issue={302} />
      <Link href="/docs" style={{ padding: 16, textAlign: 'center' }}>
        Docs
      </Link>
    </View>
  );
}
