import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

/** A full-screen spinner, or a message in its place. */
export function CenteredStatus({ message }: { message?: string }) {
  return (
    <View style={styles.container}>
      {message ? <Text style={styles.message}>{message}</Text> : <ActivityIndicator />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24 },
  message: { textAlign: 'center' },
});
