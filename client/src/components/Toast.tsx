import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { Animated, Platform, Pressable, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AppText } from '@/components/AppText';
import { useTabBarClearance } from '@/components/GlassTabBar';
import { MissingProviderError } from '@/hooks/MissingProviderError';
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
 * A message floating at the bottom of the screen, above the tab bar, that dismisses itself. Screens
 * show one through `useToast`; `ToastProvider` places it after their content.
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

type ToastContextValue = {
  /** Show a toast, in place of any already up. */
  notify: (text: string, action?: ToastMessage['action']) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

/** Shows the toasts its screens ask for, over them. Fills the space it is given. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const dismiss = useCallback(() => setToast(null), []);
  const notify = useCallback<ToastContextValue['notify']>(
    (text, action) => setToast((current) => ({ id: (current?.id ?? 0) + 1, text, action })),
    [],
  );
  const value = useMemo(() => ({ notify }), [notify]);

  return (
    <ToastContext.Provider value={value}>
      <View style={styles.fill}>
        {children}
        <Toast toast={toast} onDismiss={dismiss} />
      </View>
    </ToastContext.Provider>
  );
}

/**
 * Show toasts from the nearest `ToastProvider`.
 *
 * @throws {MissingProviderError} when called outside a `ToastProvider`.
 */
export function useToast(): ToastContextValue {
  const value = useContext(ToastContext);
  if (!value) throw new MissingProviderError('useToast', 'ToastProvider');
  return value;
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
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
