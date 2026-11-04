import { useLocalSearchParams } from 'expo-router';

import { AppText } from '@/components/AppText';
import { Screen } from '@/components/Screen';
import { guideBySlug } from '@/docs/guides';
import { Markdown } from '@/docs/Markdown';

/** One guide, by the slug in its address. */
export function GuideScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const guide = guideBySlug(slug);

  if (!guide) {
    return (
      <Screen title="Docs" back>
        <AppText tone="muted">There’s no guide here. Go back to see the ones there are.</AppText>
      </Screen>
    );
  }

  return (
    <Screen title={guide.title} back>
      <Markdown source={guide.body} />
    </Screen>
  );
}
