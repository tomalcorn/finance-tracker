import { useRouter, type Href } from 'expo-router';
import { Linking, StyleSheet, Text, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { parseMarkdown, type Block, type Inline } from '@/docs/parseMarkdown';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

function isExternal(href: string): boolean {
  return /^https?:/.test(href);
}

/**
 * A line's runs of text. Goes inside a text element, so links and bold flow with the words and take
 * its size.
 */
function Inlines({ inlines }: { inlines: readonly Inline[] }) {
  const router = useRouter();
  const { colors } = useAppTheme();

  return inlines.map((inline, index) => {
    switch (inline.kind) {
      case 'text':
        return inline.text;
      case 'strong':
        return (
          <Text key={index} style={styles.strong}>
            {inline.text}
          </Text>
        );
      case 'emphasis':
        return (
          <Text key={index} style={styles.emphasis}>
            {inline.text}
          </Text>
        );
      case 'link':
        return (
          <Text
            key={index}
            role="link"
            style={[styles.link, { color: colors.accent }]}
            onPress={() => {
              if (isExternal(inline.href)) void Linking.openURL(inline.href);
              else router.push(inline.href as Href);
            }}
          >
            {inline.text}
          </Text>
        );
    }
  });
}

function MarkdownBlock({ block }: { block: Block }) {
  const { colors } = useAppTheme();

  switch (block.kind) {
    case 'heading':
      return block.level === 2 ? (
        <AppText variant="heading" style={styles.heading}>
          {block.text}
        </AppText>
      ) : (
        <AppText role="heading" style={[styles.strong, styles.subheading]}>
          {block.text}
        </AppText>
      );
    case 'paragraph':
      return (
        <AppText>
          <Inlines inlines={block.inlines} />
        </AppText>
      );
    case 'list':
      return (
        <View style={styles.list}>
          {block.items.map((item, index) => (
            <View key={index} style={styles.item}>
              <AppText tone="muted" style={styles.marker}>
                {block.ordered ? `${index + 1}.` : '•'}
              </AppText>
              <AppText style={styles.itemText}>
                <Inlines inlines={item} />
              </AppText>
            </View>
          ))}
        </View>
      );
    case 'quote':
      return (
        <View style={[styles.quote, { backgroundColor: colors.accentSoft }]}>
          <AppText>
            <Inlines inlines={block.inlines} />
          </AppText>
        </View>
      );
    case 'table':
      return (
        <View style={[styles.table, { borderColor: colors.border }]}>
          <View style={[styles.tableRow, { backgroundColor: colors.surfaceMuted }]}>
            {block.header.map((cell, index) => (
              <AppText
                key={index}
                variant="label"
                tone="muted"
                style={index === 0 ? styles.firstCell : styles.cell}
              >
                <Inlines inlines={cell} />
              </AppText>
            ))}
          </View>
          {block.rows.map((row, rowIndex) => (
            <View
              key={rowIndex}
              style={[styles.tableRow, { borderTopColor: colors.border }, styles.ruled]}
            >
              {row.map((cell, index) => (
                <AppText
                  key={index}
                  variant="caption"
                  style={index === 0 ? styles.firstCell : styles.cell}
                >
                  <Inlines inlines={cell} />
                </AppText>
              ))}
            </View>
          ))}
        </View>
      );
  }
}

/** A page of markdown, in the theme's type and colours. */
export function Markdown({ source }: { source: string }) {
  return (
    <View style={styles.page}>
      {parseMarkdown(source).map((block, index) => (
        <MarkdownBlock key={index} block={block} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  page: { gap: SPACING.md },
  strong: { fontWeight: '600' },
  emphasis: { fontStyle: 'italic' },
  link: { textDecorationLine: 'underline' },
  heading: { marginTop: SPACING.md },
  subheading: { marginTop: SPACING.sm },
  list: { gap: SPACING.xs },
  item: { flexDirection: 'row', gap: SPACING.sm },
  marker: { minWidth: 16 },
  itemText: { flex: 1 },
  quote: { padding: SPACING.md, borderRadius: RADIUS.md },
  table: { borderWidth: StyleSheet.hairlineWidth, borderRadius: RADIUS.md, overflow: 'hidden' },
  tableRow: { flexDirection: 'row', gap: SPACING.md, padding: SPACING.md },
  ruled: { borderTopWidth: StyleSheet.hairlineWidth },
  firstCell: { flex: 2 },
  cell: { flex: 3 },
});
