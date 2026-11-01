import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Animated,
  KeyboardAvoidingView,
  Modal,
  PanResponder,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
  useWindowDimensions,
  type ViewStyle,
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
/** How far, or how fast in px/ms, a drag down must go for the sheet to close on release. */
const DISMISS_DISTANCE = 120;
const DISMISS_VELOCITY = 0.8;
/** Dragging up past the open position moves the sheet this much for every 100px of finger travel. */
const OVERDRAG_RATIO = 0.1;

// The browser would otherwise take a touch drag on the handle as a page scroll or pull-to-refresh.
const NO_TOUCH_SCROLL = Platform.select<ViewStyle>({
  web: { touchAction: 'none', userSelect: 'none' } as ViewStyle,
  default: {},
});

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
  const [drag] = useState(() => new Animated.Value(0));
  const dragHandlers = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: (_, { dx, dy }) =>
          Math.abs(dy) > 4 && Math.abs(dy) > Math.abs(dx),
        onPanResponderMove: (_, { dy }) => drag.setValue(dy),
        onPanResponderRelease: (_, { dy, vy }) => {
          if (dy > DISMISS_DISTANCE || vy > DISMISS_VELOCITY) {
            onClose();
            return;
          }
          Animated.spring(drag, { toValue: 0, ...OPEN }).start();
        },
        onPanResponderTerminate: () => Animated.spring(drag, { toValue: 0, ...OPEN }).start(),
      }),
    [drag, onClose],
  );

  if (visible && !mounted) setMounted(true);

  useEffect(() => {
    if (!mounted) return;
    if (visible) {
      drag.setValue(0);
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
  }, [drag, mounted, progress, visible]);

  const panelMotion = wide
    ? {
        opacity: progress,
        transform: [
          { scale: progress.interpolate({ inputRange: [0, 1], outputRange: [0.96, 1] }) },
        ],
      }
    : {
        transform: [
          {
            translateY: Animated.add(
              progress.interpolate({ inputRange: [0, 1], outputRange: [height, 0] }),
              drag.interpolate({
                inputRange: [-100, 0, 100],
                outputRange: [-100 * OVERDRAG_RATIO, 0, 100],
              }),
            ),
          },
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
          <View
            {...(wide ? {} : dragHandlers.panHandlers)}
            style={[styles.handleArea, !wide && NO_TOUCH_SCROLL]}
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
  handleArea: { gap: SPACING.md },
  header: { flexDirection: 'row', alignItems: 'center', gap: SPACING.md },
  title: { flex: 1 },
  scroll: { flexGrow: 0 },
  content: { gap: SPACING.md },
  footer: { gap: SPACING.sm },
});
