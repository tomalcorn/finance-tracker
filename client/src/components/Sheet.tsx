import { useEffect, useState, type ReactNode } from 'react';
import {
  Animated,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
  useWindowDimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { AppText } from '@/components/AppText';
import { useKeyboardInset } from '@/components/keyboardInset';
import { useAppTheme } from '@/theme/theme';
import { BACKDROP, RADIUS, SPACING, WIDE_BREAKPOINT } from '@/theme/tokens';

type SheetProps = {
  visible: boolean;
  /** Called when the person asks to close it: the backdrop, Escape, or the Close link. */
  onClose: () => void;
  title: string;
  children: ReactNode;
  /** Pinned below the content, e.g. Save and Cancel buttons. */
  footer?: ReactNode;
};

const USE_NATIVE_DRIVER = Platform.OS !== 'web';
const OPEN = { stiffness: 380, damping: 36, mass: 1, useNativeDriver: USE_NATIVE_DRIVER };
const CLOSE_MS = 180;
const MAX_DIALOG_WIDTH = 480;

/**
 * A panel over the current screen, for adding or editing something: a sheet sliding up from the
 * bottom on a phone, a centred dialog on a wide window. It stays mounted while it animates out.
 */
export function Sheet({ visible, onClose, title, children, footer }: SheetProps) {
  const { colors } = useAppTheme();
  const insets = useSafeAreaInsets();
  const keyboardInset = useKeyboardInset();
  const { width, height } = useWindowDimensions();
  const wide = width >= WIDE_BREAKPOINT;
  const [mounted, setMounted] = useState(visible);
  const [progress] = useState(() => new Animated.Value(0));

  if (visible && !mounted) setMounted(true);

  useEffect(() => {
    if (!mounted) return;
    if (visible) {
      Animated.spring(progress, { toValue: 1, ...OPEN }).start();
      return;
    }
    Animated.timing(progress, {
      toValue: 0,
      duration: CLOSE_MS,
      useNativeDriver: USE_NATIVE_DRIVER,
    }).start(({ finished }) => {
      if (finished) setMounted(false);
    });
  }, [mounted, progress, visible]);

  const panelMotion = wide
    ? {
        opacity: progress,
        transform: [
          { scale: progress.interpolate({ inputRange: [0, 1], outputRange: [0.96, 1] }) },
        ],
      }
    : {
        transform: [
          { translateY: progress.interpolate({ inputRange: [0, 1], outputRange: [height, 0] }) },
        ],
      };

  return (
    <Modal
      visible={mounted}
      transparent
      animationType="none"
      onRequestClose={onClose}
      statusBarTranslucent
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={[
          styles.layer,
          wide ? styles.centred : styles.bottom,
          { paddingBottom: keyboardInset },
        ]}
      >
        <Animated.View style={[StyleSheet.absoluteFill, { opacity: progress }]}>
          <Pressable
            aria-label="Close"
            onPress={onClose}
            style={[StyleSheet.absoluteFill, { backgroundColor: BACKDROP }]}
          />
        </Animated.View>
        <Animated.View
          style={[
            styles.panel,
            wide ? styles.dialog : styles.sheet,
            {
              backgroundColor: colors.surface,
              maxHeight: (height - keyboardInset) * 0.9,
              paddingBottom: wide
                ? SPACING.lg
                : SPACING.lg + (keyboardInset > 0 ? 0 : insets.bottom),
            },
            panelMotion,
          ]}
        >
          {wide ? null : <View style={[styles.grabber, { backgroundColor: colors.border }]} />}
          <View style={styles.header}>
            <AppText variant="heading" style={styles.title}>
              {title}
            </AppText>
            <Pressable role="button" onPress={onClose} hitSlop={SPACING.md}>
              <AppText variant="label" tone="accent">
                Close
              </AppText>
            </Pressable>
          </View>
          <ScrollView
            keyboardShouldPersistTaps="handled"
            contentContainerStyle={styles.content}
            style={styles.scroll}
          >
            {children}
          </ScrollView>
          {footer ? <View style={styles.footer}>{footer}</View> : null}
        </Animated.View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  layer: { flex: 1 },
  bottom: { justifyContent: 'flex-end' },
  centred: { justifyContent: 'center', alignItems: 'center', padding: SPACING.xl },
  panel: { paddingHorizontal: SPACING.lg, gap: SPACING.md },
  sheet: {
    borderTopLeftRadius: RADIUS.lg,
    borderTopRightRadius: RADIUS.lg,
    paddingTop: SPACING.sm,
  },
  dialog: {
    width: '100%',
    maxWidth: MAX_DIALOG_WIDTH,
    borderRadius: RADIUS.lg,
    paddingTop: SPACING.lg,
  },
  grabber: { alignSelf: 'center', width: 36, height: 5, borderRadius: RADIUS.pill },
  header: { flexDirection: 'row', alignItems: 'center', gap: SPACING.md },
  title: { flex: 1 },
  scroll: { flexGrow: 0 },
  content: { gap: SPACING.md },
  footer: { gap: SPACING.sm },
});
