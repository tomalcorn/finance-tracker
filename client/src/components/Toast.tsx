import { useEffect, useState } from 'react';
import { Animated, Platform, Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AppText } from '@/components/AppText';
import { useTabBarClearance } from '@/components/GlassTabBar';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

/** A short message, and optionally one action on what it reports. */
export type ToastMessage = {
  /** Tells one toast from the next, so the same text shown twice restarts the timer. */
  id: number;
  text: string;
  action?: { label: string; onPress: () => void };
};

type ToastProps = {
  toast: ToastMessage | null;
  /** Called once the toast has been on screen long enough, or its action was taken. */
  onDismiss: () => void;
};

/** How long a toast stays up: long enough to reach its action. */
export const TOAST_MS = 4000;

const USE_NATIVE_DRIVER = Platform.OS !== 'web';

/**
 * A message floating at the bottom of the screen, above the tab bar, that dismisses itself. Place
 * it after the screen's content, in a container that fills the screen.
 */
export function Toast({ toast, onDismiss }: ToastProps) {
  const { colors } = useAppTheme();
  const insets = useSafeAreaInsets();
  const clearance = useTabBarClearance();
  const [shown] = useState(() => new Animated.Value(0));

  useEffect(() => {
    if (!toast) return;
    shown.setValue(0);
    Animated.spring(shown, { toValue: 1, useNativeDriver: USE_NATIVE_DRIVER }).start();
    const timer = setTimeout(onDismiss, TOAST_MS);
    return () => clearTimeout(timer);
  }, [onDismiss, shown, toast]);

  if (!toast) return null;
  const { action } = toast;

  return (
    <View
      pointerEvents="box-none"
      style={[styles.layer, { bottom: (clearance || insets.bottom) + SPACING.md }]}
    >
      <Animated.View
        role="status"
        aria-live="polite"
        style={[
          styles.toast,
          { backgroundColor: colors.text },
          {
            opacity: shown,
            transform: [
              { translateY: shown.interpolate({ inputRange: [0, 1], outputRange: [16, 0] }) },
            ],
          },
        ]}
      >
        <AppText style={[styles.text, { color: colors.background }]}>{toast.text}</AppText>
        {action ? (
          <Pressable
            role="button"
            onPress={() => {
              action.onPress();
              onDismiss();
            }}
            hitSlop={SPACING.md}
          >
            <AppText variant="label" style={[styles.action, { color: colors.background }]}>
              {action.label}
            </AppText>
          </Pressable>
        ) : null}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  layer: { position: 'absolute', left: 0, right: 0, alignItems: 'center' },
  toast: {
    maxWidth: 480,
    marginHorizontal: SPACING.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.lg,
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
    borderRadius: RADIUS.lg,
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 4,
  },
  text: { flexShrink: 1 },
  action: { fontWeight: '700', textDecorationLine: 'underline' },
});
