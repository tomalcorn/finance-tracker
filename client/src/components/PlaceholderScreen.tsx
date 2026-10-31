import { AppText } from '@/components/AppText';
import { Card } from '@/components/Card';
import { Screen } from '@/components/Screen';

type PlaceholderScreenProps = {
  title: string;
  issue: number;
  /** Show a link back, for a screen pushed over the tabs. */
  back?: boolean;
};

/** Stand-in for a screen that has not been built yet, naming the issue that builds it. */
export function PlaceholderScreen({ title, issue, back = false }: PlaceholderScreenProps) {
  return (
    <Screen title={title} back={back}>
      <Card>
        <AppText tone="muted">Coming in #{issue}.</AppText>
      </Card>
    </Screen>
  );
}
