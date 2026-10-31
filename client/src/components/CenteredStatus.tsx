import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { SPACING } from '@/theme/tokens';

/** A full-screen spinner, or a message in its place. */
export function CenteredStatus({ message }: { message?: string }) {
  const { colors } = useAppTheme();
  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {message ? (
        <AppText tone="muted" style={styles.message}>
          {message}
        </AppText>
      ) : (
        <ActivityIndicator color={colors.accent} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: SPACING.xl },
  message: { textAlign: 'center' },
});
