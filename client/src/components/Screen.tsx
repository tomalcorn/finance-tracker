import type { ReactNode } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import { useAppTheme } from '@/theme/theme';
import { MAX_CONTENT_WIDTH, SPACING } from '@/theme/tokens';

type ScreenProps = {
  children: ReactNode;
  /** Centre the content vertically, for a screen with little on it. */
  centred?: boolean;
};

/** A screen's scrolling page: the theme background and one column, capped in width on desktop. */
export function Screen({ children, centred = false }: ScreenProps) {
  const { colors } = useAppTheme();
  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentContainerStyle={[styles.content, centred && styles.centred]}
    >
      <View style={styles.column}>{children}</View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, alignItems: 'center', padding: SPACING.lg },
  centred: { justifyContent: 'center' },
  column: { width: '100%', maxWidth: MAX_CONTENT_WIDTH, gap: SPACING.lg },
});
