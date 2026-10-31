import { useState, type ReactNode } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

export type DenseColumn<Row> = {
  key: string;
  label: string;
  /** What the cell shows: plain text, or any node, e.g. an `Amount`. */
  render: (row: Row) => ReactNode;
  /** A fixed width. Without one, the column shares the leftover space with the others. */
  width?: number;
  /** Right-align numbers so their digits line up. */
  align?: 'left' | 'right';
};

type DenseTableProps<Row> = {
  columns: readonly DenseColumn<Row>[];
  rows: readonly Row[];
  rowKey: (row: Row) => string;
  onRowPress?: (row: Row) => void;
  /** Shown in place of the rows when there are none. */
  empty?: string;
};

/** Columns without a width never shrink below this; past it, the table scrolls sideways. */
const MIN_FLEX_COLUMN_WIDTH = 64;

/**
 * A compact table for the few places that need to compare many rows at once. Prefer `Card` with
 * `ListRow`s everywhere else.
 */
export function DenseTable<Row>({
  columns,
  rows,
  rowKey,
  onRowPress,
  empty = 'Nothing here yet.',
}: DenseTableProps<Row>) {
  const { colors } = useAppTheme();
  const [frameWidth, setFrameWidth] = useState(0);
  const minWidth = columns.reduce(
    (sum, column) => sum + (column.width ?? MIN_FLEX_COLUMN_WIDTH),
    0,
  );
  // Inside a sideways scroller the flexible columns would grow to fit their longest text, so the
  // table is sized explicitly: the visible width, or the columns' minimum when that is wider.
  const tableWidth = Math.max(frameWidth, minWidth);

  const cell = (column: DenseColumn<Row>, content: ReactNode) => (
    <View
      key={column.key}
      style={[
        styles.cell,
        column.width ? { width: column.width } : styles.flexCell,
        column.align === 'right' && styles.right,
      ]}
    >
      {typeof content === 'string' || typeof content === 'number' ? (
        <AppText variant="caption" numberOfLines={1}>
          {content}
        </AppText>
      ) : (
        content
      )}
    </View>
  );

  return (
    <View
      role="table"
      style={[styles.frame, { backgroundColor: colors.surface, borderColor: colors.border }]}
    >
      <ScrollView horizontal onLayout={(event) => setFrameWidth(event.nativeEvent.layout.width)}>
        <View style={{ width: tableWidth }}>
          <View role="row" style={[styles.row, styles.header, { borderColor: colors.border }]}>
            {columns.map((column) =>
              cell(
                column,
                <AppText variant="caption" tone="muted" numberOfLines={1} style={styles.headerText}>
                  {column.label}
                </AppText>,
              ),
            )}
          </View>
          {rows.length === 0 ? (
            <AppText variant="caption" tone="muted" style={styles.empty}>
              {empty}
            </AppText>
          ) : (
            rows.map((row, index) => {
              const cells = columns.map((column) => cell(column, column.render(row)));
              const rowStyle = [
                styles.row,
                index > 0 && [styles.divided, { borderColor: colors.border }],
              ];
              return onRowPress ? (
                <Pressable
                  key={rowKey(row)}
                  role="row"
                  onPress={() => onRowPress(row)}
                  style={({ pressed }) => [
                    rowStyle,
                    pressed && { backgroundColor: colors.surfaceMuted },
                  ]}
                >
                  {cells}
                </Pressable>
              ) : (
                <View key={rowKey(row)} role="row" style={rowStyle}>
                  {cells}
                </View>
              );
            })
          )}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  frame: { borderRadius: RADIUS.lg, borderWidth: StyleSheet.hairlineWidth, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', minHeight: 40 },
  header: { minHeight: 34, borderBottomWidth: StyleSheet.hairlineWidth },
  headerText: { fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.4, fontSize: 11 },
  divided: { borderTopWidth: StyleSheet.hairlineWidth },
  cell: { paddingHorizontal: SPACING.sm, paddingVertical: SPACING.xs },
  flexCell: { flex: 1, minWidth: MIN_FLEX_COLUMN_WIDTH },
  right: { alignItems: 'flex-end' },
  empty: { padding: SPACING.lg, textAlign: 'center' },
});
