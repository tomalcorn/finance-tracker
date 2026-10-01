import { StyleSheet, Text, View } from 'react-native';

type PlaceholderScreenProps = {
  title: string;
  issue: number;
};

/** Stand-in for a screen that has not been built yet, naming the issue that builds it. */
export function PlaceholderScreen({ title, issue }: PlaceholderScreenProps) {
  return (
    <View style={styles.container}>
      <Text role="heading" style={styles.title}>
        {title}
      </Text>
      <Text>Coming in #{issue}.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  title: {
    fontSize: 24,
    fontWeight: '600',
  },
});
