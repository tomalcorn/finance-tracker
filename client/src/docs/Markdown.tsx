import { useRouter, type Href } from 'expo-router';
import { lexer, type MarkedToken, type Token, type Tokens } from 'marked';
import { Linking, StyleSheet, Text, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

/** Join a source line's wrapping back up, which `Text` would otherwise show as a line break. */
function unwrapped(text: string): string {
  return text.replace(/\s*\n\s*/g, ' ');
}

function InlineLink({ token }: { token: Tokens.Link }) {
  const router = useRouter();
  const { colors } = useAppTheme();
  const external = /^https?:/.test(token.href);

  function follow() {
    if (external) void Linking.openURL(token.href);
    else router.push(token.href as Href);
  }

  return (
    <Text role="link" style={[styles.link, { color: colors.accent }]} onPress={follow}>
      <Inlines tokens={token.tokens} />
    </Text>
  );
}

function InlineToken({ token }: { token: MarkedToken }) {
  switch (token.type) {
    case 'strong':
      return (
        <Text style={styles.strong}>
          <Inlines tokens={token.tokens} />
        </Text>
      );
    case 'em':
      return (
        <Text style={styles.emphasis}>
          <Inlines tokens={token.tokens} />
        </Text>
      );
    case 'link':
      return <InlineLink token={token} />;
    case 'text':
      return token.tokens ? <Inlines tokens={token.tokens} /> : unwrapped(token.text);
    default:
      return 'text' in token ? unwrapped(token.text) : null;
  }
}

/** A line's runs of text. Goes inside a text element, so they flow with the words and take its size. */
function Inlines({ tokens }: { tokens: readonly Token[] }) {
  return tokens.map((token, index) => <InlineToken key={index} token={token as MarkedToken} />);
}

function HeadingBlock({ token }: { token: Tokens.Heading }) {
  if (token.depth <= 2) {
    return (
      <AppText variant="heading" style={styles.heading}>
        <Inlines tokens={token.tokens} />
      </AppText>
    );
  }
  return (
    <AppText role="heading" style={[styles.strong, styles.subheading]}>
      <Inlines tokens={token.tokens} />
    </AppText>
  );
}

function ParagraphBlock({ token }: { token: Tokens.Paragraph }) {
  return (
    <AppText>
      <Inlines tokens={token.tokens} />
    </AppText>
  );
}

function ListBlock({ token }: { token: Tokens.List }) {
  return (
    <View style={styles.list}>
      {token.items.map((item, index) => (
        <View key={index} style={styles.item}>
          <AppText tone="muted" style={styles.marker}>
            {token.ordered ? `${index + 1}.` : '•'}
          </AppText>
          <AppText style={styles.itemText}>
            <Inlines tokens={item.tokens} />
          </AppText>
        </View>
      ))}
    </View>
  );
}

function QuoteBlock({ token }: { token: Tokens.Blockquote }) {
  const { colors } = useAppTheme();

  return (
    <View style={[styles.quote, { backgroundColor: colors.accentSoft }]}>
      <Blocks tokens={token.tokens} />
    </View>
  );
}

function TableBlock({ token }: { token: Tokens.Table }) {
  const { colors } = useAppTheme();

  return (
    <View style={[styles.table, { borderColor: colors.border }]}>
      <View style={[styles.tableRow, { backgroundColor: colors.surfaceMuted }]}>
        {token.header.map((cell, index) => (
          <AppText
            key={index}
            variant="label"
            tone="muted"
            style={index === 0 ? styles.firstCell : styles.cell}
          >
            <Inlines tokens={cell.tokens} />
          </AppText>
        ))}
      </View>
      {token.rows.map((row, rowIndex) => (
        <View
          key={rowIndex}
          style={[styles.tableRow, styles.ruled, { borderTopColor: colors.border }]}
        >
          {row.map((cell, index) => (
            <AppText
              key={index}
              variant="caption"
              style={index === 0 ? styles.firstCell : styles.cell}
            >
              <Inlines tokens={cell.tokens} />
            </AppText>
          ))}
        </View>
      ))}
    </View>
  );
}

function Block({ token }: { token: MarkedToken }) {
  switch (token.type) {
    case 'heading':
      return <HeadingBlock token={token} />;
    case 'paragraph':
      return <ParagraphBlock token={token} />;
    case 'list':
      return <ListBlock token={token} />;
    case 'blockquote':
      return <QuoteBlock token={token} />;
    case 'table':
      return <TableBlock token={token} />;
    default:
      return null;
  }
}

function Blocks({ tokens }: { tokens: readonly Token[] }) {
  return (
    <View style={styles.blocks}>
      {tokens.map((token, index) => (
        <Block key={index} token={token as MarkedToken} />
      ))}
    </View>
  );
}

/**
 * A page of markdown, in the theme's type and colours. It draws headings, paragraphs, flat lists,
 * tables and quotes, with bold, italic and links inside them, and leaves out anything else.
 */
export function Markdown({ source }: { source: string }) {
  return <Blocks tokens={lexer(source)} />;
}

const styles = StyleSheet.create({
  blocks: { gap: SPACING.md },
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
