import { Children, Fragment, type ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { interactiveBackground } from '@/components/interaction';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

type CardProps = {
  children: ReactNode;
  /** A small heading above the card. */
  title?: string;
  /** Beside the heading, or under it when there is no room. */
  titleDetail?: string;
  /** Lay the children out edge to edge with a divider between each, for a list of rows. */
  list?: boolean;
  /** Make the whole card a button, e.g. to open more detail. */
  onPress?: () => void;
  /** Names the card as a button, when it has `onPress`. */
  label?: string;
  /** Stretch to the height of whatever holds it, e.g. to match the other cards in a row. */
  fill?: boolean;
};

/** A rounded surface grouping related content, or a list of `ListRow`s. */
export function Card({
  children,
  title,
  titleDetail,
  list = false,
  onPress,
  label,
  fill = false,
}: CardProps) {
  const { colors } = useAppTheme();
  const items = Children.toArray(children);
  const content = list
    ? items.map((item, index) => (
        <Fragment key={index}>
          {index > 0 ? <View style={[styles.divider, { backgroundColor: colors.border }]} /> : null}
          {item}
        </Fragment>
      ))
    : children;

  return (
    <View style={[styles.group, fill && styles.fill]}>
      {title ? <CardHeading title={title} detail={titleDetail} /> : null}
      {onPress ? (
        <Pressable
          role="button"
          aria-label={label ?? title}
          onPress={onPress}
          style={(state) => [
            styles.card,
            fill && styles.fill,
            {
              backgroundColor: interactiveBackground(state, colors, colors.surface),
              borderColor: colors.border,
            },
            !list && styles.padded,
          ]}
        >
          {content}
        </Pressable>
      ) : (
        <View
          style={[
            styles.card,
            fill && styles.fill,
            { backgroundColor: colors.surface, borderColor: colors.border },
            !list && styles.padded,
          ]}
        >
          {content}
        </View>
      )}
    </View>
  );
}

/** The small heading above a card, or above a group of cards. */
export function CardHeading({ title, detail }: { title: string; detail?: string }) {
  return (
    <View style={styles.heading}>
      <AppText variant="label" tone="muted">
        {title}
      </AppText>
      {detail ? <AppText variant="label">{detail}</AppText> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  group: { gap: SPACING.sm },
  fill: { flex: 1 },
  heading: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    columnGap: SPACING.md,
    paddingHorizontal: SPACING.xs,
  },
  card: { borderRadius: RADIUS.lg, borderWidth: StyleSheet.hairlineWidth, overflow: 'hidden' },
  padded: { padding: SPACING.lg, gap: SPACING.md },
  divider: { height: StyleSheet.hairlineWidth, marginLeft: SPACING.lg },
});
