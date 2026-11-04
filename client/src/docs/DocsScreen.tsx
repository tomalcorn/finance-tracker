import { SymbolView } from 'expo-symbols';
import { useRouter } from 'expo-router';

import { Card } from '@/components/Card';
import { ListRow } from '@/components/ListRow';
import { Screen } from '@/components/Screen';
import { GUIDES } from '@/docs/guides';
import { useAppTheme } from '@/theme/theme';

const ICON_SIZE = 22;

/** The list of guides. */
export function DocsScreen() {
  const { colors } = useAppTheme();
  const router = useRouter();

  return (
    <Screen title="Docs" back>
      <Card list>
        {GUIDES.map((guide) => (
          <ListRow
            key={guide.slug}
            title={guide.title}
            leading={<SymbolView name={guide.icon} size={ICON_SIZE} tintColor={colors.accent} />}
            onPress={() => router.push({ pathname: '/docs/[slug]', params: { slug: guide.slug } })}
          />
        ))}
      </Card>
    </Screen>
  );
}
