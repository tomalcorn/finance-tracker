import { Children, Fragment, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

type CardProps = {
  children: ReactNode;
  /** A small heading above the card. */
  title?: string;
  /** Lay the children out edge to edge with a divider between each, for a list of rows. */
  list?: boolean;
};

/** A rounded surface grouping related content, or a list of `ListRow`s. */
export function Card({ children, title, list = false }: CardProps) {
  const { colors } = useAppTheme();
  const items = Children.toArray(children);

  return (
    <View style={styles.group}>
      {title ? (
        <AppText variant="label" tone="muted" style={styles.title}>
          {title}
        </AppText>
      ) : null}
      <View
        style={[
          styles.card,
          { backgroundColor: colors.surface, borderColor: colors.border },
          !list && styles.padded,
        ]}
      >
        {list
          ? items.map((item, index) => (
              <Fragment key={index}>
                {index > 0 ? (
                  <View style={[styles.divider, { backgroundColor: colors.border }]} />
                ) : null}
                {item}
              </Fragment>
            ))
          : children}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  group: { gap: SPACING.sm },
  title: { paddingHorizontal: SPACING.xs },
  card: { borderRadius: RADIUS.lg, borderWidth: StyleSheet.hairlineWidth, overflow: 'hidden' },
  padded: { padding: SPACING.lg, gap: SPACING.md },
  divider: { height: StyleSheet.hairlineWidth, marginLeft: SPACING.lg },
});
