import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import type { DateFieldProps } from '@/components/DateField';
import { FIELD_ROW_HEIGHT } from '@/components/Field';
import { NO_FOCUS_RING } from '@/components/fieldFocus';
import { interactiveBackground, type InteractionState } from '@/components/interaction';
import { addDays } from '@/domain/dates';
import { formatFieldDay, isCalendarDate, relativeDayName } from '@/theme/formatDate';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

const CALENDAR: SymbolViewProps['name'] = { ios: 'calendar', web: 'calendar_today' };

/** Shown in a date field with no date in it. */
const NO_DATE = 'No date';

type DateChipsProps = Pick<DateFieldProps, 'label' | 'value' | 'onChange'> & {
  today: string;
  /** Offer Today and Yesterday. */
  quickPicks: boolean;
  /** Offer Clear while a date is set. */
  optional: boolean;
};

/**
 * The chips beside a date field's label, which set the date in one tap: Today and Yesterday, and
 * Clear when the date is optional and set.
 */
export function DateChips({ label, value, onChange, today, quickPicks, optional }: DateChipsProps) {
  const picks = quickPicks
    ? [
        { name: 'Today', date: today },
        { name: 'Yesterday', date: addDays(today, -1) },
      ]
    : [];

  return (
    <>
      {picks.map(({ name, date }) => (
        <Chip
          key={name}
          label={name}
          accessibleLabel={`${label}: ${name.toLowerCase()}`}
          selected={value === date}
          onPress={() => onChange(date)}
        />
      ))}
      {optional && value !== '' ? (
        <Chip
          label="Clear"
          accessibleLabel={`Clear ${label.toLowerCase()}`}
          onPress={() => onChange('')}
        />
      ) : null}
    </>
  );
}

type ChipProps = {
  label: string;
  /** What assistive technology announces, naming the field the chip sets. */
  accessibleLabel: string;
  /** Whether the field already holds this chip's date. */
  selected?: boolean;
  onPress: () => void;
};

function Chip({ label, accessibleLabel, selected, onPress }: ChipProps) {
  const { colors } = useAppTheme();
  return (
    <Pressable
      role="button"
      aria-label={accessibleLabel}
      aria-pressed={selected}
      hitSlop={{ top: 8, bottom: 8, left: 4, right: 4 }}
      onPress={onPress}
      style={(state: InteractionState) => [
        styles.chip,
        NO_FOCUS_RING,
        {
          backgroundColor: selected
            ? colors.accentSoft
            : interactiveBackground(state, colors, colors.surfaceMuted),
          borderColor: state.focused ? colors.accent : 'transparent',
        },
      ]}
    >
      <AppText variant="caption" tone={selected ? 'accent' : 'muted'} style={styles.chipText}>
        {label}
      </AppText>
    </Pressable>
  );
}

/**
 * A date in words: the day, e.g. `Thu 12 Nov`, and `Today`, `Yesterday` or `Tomorrow` when it is
 * one of them.
 */
type Words = { relative: string | null; day: string };

/** A field's date in words, or null for text that isn't a date. */
function dateInWords(value: string, today: string): Words | null {
  if (!isCalendarDate(value)) return null;
  return { relative: relativeDayName(value, today), day: formatFieldDay(value, today) };
}

/** What is spoken for a field's date: the day in words, or that there is none. */
export function spokenDate(value: string, today: string): string {
  if (value === '') return NO_DATE;
  const words = dateInWords(value, today);
  if (words === null) return value;
  return words.relative ? `${words.relative}, ${words.day}` : words.day;
}

type ValueProps = { value: string; today: string; trailing?: SymbolViewProps['name'] };

/**
 * The inside of a date field: a calendar icon and the date in words, e.g. `Today  Thu 12 Nov` or
 * `Mon 10 Nov`, or `No date` when empty. Text that isn't a date is shown as it is.
 */
export function DateFieldValue({ value, today, trailing }: ValueProps) {
  const { colors } = useAppTheme();
  return (
    <View style={styles.value}>
      <SymbolView name={CALENDAR} size={18} tintColor={colors.textMuted} />
      <View style={styles.text} aria-live="polite">
        <DateWords value={value} today={today} />
      </View>
      {trailing ? <SymbolView name={trailing} size={20} tintColor={colors.textMuted} /> : null}
    </View>
  );
}

function DateWords({ value, today }: Pick<ValueProps, 'value' | 'today'>) {
  if (value === '') {
    return (
      <AppText tone="muted" numberOfLines={1}>
        {NO_DATE}
      </AppText>
    );
  }
  const words = dateInWords(value, today);
  if (words === null) return <AppText numberOfLines={1}>{value}</AppText>;
  if (words.relative === null) return <AppText numberOfLines={1}>{words.day}</AppText>;
  return (
    <AppText numberOfLines={1}>
      {words.relative}
      <AppText tone="muted">{`  ${words.day}`}</AppText>
    </AppText>
  );
}

const styles = StyleSheet.create({
  chip: {
    minHeight: 26,
    justifyContent: 'center',
    paddingHorizontal: SPACING.sm + 2,
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  chipText: { fontWeight: '600' },
  value: {
    minHeight: FIELD_ROW_HEIGHT,
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingHorizontal: SPACING.md,
  },
  text: { flex: 1 },
});
