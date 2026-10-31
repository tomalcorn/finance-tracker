import { AppText } from '@/components/AppText';
import { Card } from '@/components/Card';
import { Screen } from '@/components/Screen';

type PlaceholderScreenProps = {
  title: string;
  issue: number;
};

/** Stand-in for a screen that has not been built yet, naming the issue that builds it. */
export function PlaceholderScreen({ title, issue }: PlaceholderScreenProps) {
  return (
    <Screen centred>
      <Card>
        <AppText variant="heading">{title}</AppText>
        <AppText tone="muted">Coming in #{issue}.</AppText>
      </Card>
    </Screen>
  );
}
