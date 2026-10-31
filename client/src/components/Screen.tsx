import { useRouter } from 'expo-router';
import type { ReactNode } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AppText } from '@/components/AppText';
import { useTabBarClearance } from '@/components/GlassTabBar';
import { useAppTheme } from '@/theme/theme';
import { MAX_CONTENT_WIDTH, SPACING } from '@/theme/tokens';

type ScreenProps = {
  children: ReactNode;
  /** The large title at the top of the page. */
  title?: string;
  /** Show a link back to the previous screen above the title, for a screen pushed over the tabs. */
  back?: boolean;
  /** Centre the content vertically, for a screen with little on it. */
  centred?: boolean;
};

/**
 * A screen's scrolling page: the theme background and one column, capped in width on desktop,
 * clear of the status bar at the top. Inside the tabs, its content scrolls under the floating tab
 * bar but always clears it.
 */
export function Screen({ children, title, back = false, centred = false }: ScreenProps) {
  const { colors } = useAppTheme();
  const insets = useSafeAreaInsets();
  const clearance = useTabBarClearance();

  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentContainerStyle={[
        styles.content,
        centred && styles.centred,
        { paddingTop: SPACING.lg + insets.top, paddingBottom: SPACING.lg + clearance },
      ]}
    >
      <View style={styles.column}>
        {back || title ? (
          <View style={styles.heading}>
            {back ? <BackLink /> : null}
            {title ? <AppText variant="title">{title}</AppText> : null}
          </View>
        ) : null}
        {children}
      </View>
    </ScrollView>
  );
}

/** Back to the previous screen, or home when the screen was opened directly. */
function BackLink() {
  const router = useRouter();
  return (
    <Pressable
      role="link"
      onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))}
      hitSlop={SPACING.md}
      style={({ pressed }) => [styles.back, pressed && styles.pressed]}
    >
      <AppText variant="label" tone="accent">
        ‹ Back
      </AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1, alignItems: 'center', paddingHorizontal: SPACING.lg },
  centred: { justifyContent: 'center' },
  column: { width: '100%', maxWidth: MAX_CONTENT_WIDTH, gap: SPACING.lg },
  heading: { gap: SPACING.xs, marginTop: SPACING.sm },
  back: { alignSelf: 'flex-start' },
  pressed: { opacity: 0.6 },
});
