import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import { NO_FOCUS_RING } from '@/components/fieldFocus';
import { type InteractionState } from '@/components/interaction';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING, type Palette } from '@/theme/tokens';

const PREVIOUS: SymbolViewProps['name'] = { ios: 'chevron.left', web: 'chevron_left' };
const NEXT: SymbolViewProps['name'] = { ios: 'chevron.right', web: 'chevron_right' };
const ZOOM_OUT: SymbolViewProps['name'] = { ios: 'chevron.down', web: 'expand_more' };

/** An arrow that pages the calendar. With no `onPress` it is disabled, at an end of the range. */
export type CalendarArrow = { label: string; onPress?: () => void };

type CalendarHeaderProps = {
  /** What the calendar shows, e.g. `November 2026`. */
  title: string;
  /** Makes the title a button, announced as the title and the hint, e.g. `choose a month`. */
  zoomOut?: { hint: string; onPress: () => void };
  previous: CalendarArrow;
  next: CalendarArrow;
};

/** The calendar's banner: what it shows, between arrows that page back and forward. */
export function CalendarHeader({ title, zoomOut, previous, next }: CalendarHeaderProps) {
  const { colors } = useAppTheme();

  return (
    <View style={styles.header}>
      <Arrow symbol={PREVIOUS} {...previous} />
      <View style={styles.titleSlot}>
        {zoomOut ? (
          <Pressable
            role="button"
            aria-label={`${title}, ${zoomOut.hint}`}
            onPress={zoomOut.onPress}
            style={(state: InteractionState) => [
              styles.title,
              NO_FOCUS_RING,
              buttonColours(colors, state),
            ]}
          >
            <AppText variant="label" aria-live="polite">
              {title}
            </AppText>
            <SymbolView name={ZOOM_OUT} size={16} tintColor={colors.textMuted} />
          </Pressable>
        ) : (
          <AppText variant="label" aria-live="polite" style={styles.titleText}>
            {title}
          </AppText>
        )}
      </View>
      <Arrow symbol={NEXT} {...next} />
    </View>
  );
}

function Arrow({ symbol, label, onPress }: CalendarArrow & { symbol: SymbolViewProps['name'] }) {
  const { colors } = useAppTheme();
  const disabled = onPress === undefined;

  return (
    <Pressable
      role="button"
      aria-label={label}
      disabled={disabled}
      hitSlop={4}
      onPress={onPress}
      style={(state: InteractionState) => [
        styles.arrow,
        NO_FOCUS_RING,
        // A disabled arrow doesn't answer the pointer, though it keeps the ring if it has focus.
        buttonColours(colors, disabled ? { ...state, pressed: false, hovered: false } : state),
        disabled && styles.disabled,
      ]}
    >
      <SymbolView name={symbol} size={20} tintColor={colors.text} />
    </Pressable>
  );
}

function buttonColours(colors: Pick<Palette, 'accent' | 'border'>, state: InteractionState) {
  return {
    backgroundColor: state.pressed || state.hovered ? colors.border : 'transparent',
    borderColor: state.focused ? colors.accent : 'transparent',
  };
}

const BUTTON_SIZE = 36;

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: SPACING.sm },
  titleSlot: { flex: 1, alignItems: 'center' },
  title: {
    minHeight: BUTTON_SIZE,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    paddingLeft: SPACING.md,
    paddingRight: SPACING.sm,
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  titleText: { lineHeight: BUTTON_SIZE },
  arrow: {
    width: BUTTON_SIZE,
    height: BUTTON_SIZE,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  disabled: { opacity: 0.3 },
});
