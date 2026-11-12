import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText } from '@/components/AppText';
import type { DateFieldProps } from '@/components/DateField';
import { NO_FOCUS_RING } from '@/components/fieldFocus';
import { interactiveBackground, type InteractionState } from '@/components/interaction';
import { addDays, formatFieldDay, isCalendarDate, relativeDayName } from '@/theme/formatDate';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

const CALENDAR: SymbolViewProps['name'] = { ios: 'calendar', web: 'calendar_today' };

/** The height inside a date field's 1.5px border, so the field stands as tall as a `TextField`. */
export const FIELD_INNER_HEIGHT = 41;

/** Shown in a date field with no date in it. */
export const NO_DATE = 'No date';

type HeaderProps = Pick<DateFieldProps, 'label' | 'value' | 'onChange' | 'optional'> & {
  labelId: string;
  today: string;
  /** Offer Today and Yesterday as one-tap choices. */
  quickPicks: boolean;
};

/**
 * A date field's label, with chips beside it that set the date in one tap: Today and Yesterday,
 * and Clear when the date is optional and set.
 */
export function DateFieldHeader({
  label,
  labelId,
  value,
  onChange,
  optional,
  today,
  quickPicks,
}: HeaderProps) {
  const chips: { label: string; date: string }[] = [];
  if (quickPicks) {
    chips.push({ label: 'Today', date: today }, { label: 'Yesterday', date: addDays(today, -1) });
  }

  return (
    <View style={styles.header}>
      <AppText variant="label" nativeID={labelId} style={styles.label}>
        {label}
      </AppText>
      {chips.map((chip) => (
        <Chip
          key={chip.label}
          label={chip.label}
          accessibleLabel={`${label}: ${chip.label.toLowerCase()}`}
          selected={value === chip.date}
          onPress={() => onChange(chip.date)}
        />
      ))}
      {optional && value !== '' ? (
        <Chip
          label="Clear"
          accessibleLabel={`Clear ${label.toLowerCase()}`}
          onPress={() => onChange('')}
        />
      ) : null}
    </View>
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

/** What is spoken for a field's date: the day in words, or that there is none. */
export function spokenDate(value: string, today: string): string {
  if (value === '') return NO_DATE;
  if (!isCalendarDate(value)) return value;
  const relative = relativeDayName(value, today);
  const day = formatFieldDay(value, today);
  return relative ? `${relative}, ${day}` : day;
}

type ValueProps = { value: string; today: string; trailing?: SymbolViewProps['name'] };

/**
 * The inside of a date field: a calendar icon and the date in words, e.g. `Today  Thu 12 Nov` or
 * `Mon 10 Nov`, or `No date` when empty. Text that isn't a date is shown as it is.
 */
export function DateFieldValue({ value, today, trailing }: ValueProps) {
  const { colors } = useAppTheme();
  const date = isCalendarDate(value) ? value : null;
  const relative = date ? relativeDayName(date, today) : null;

  return (
    <View style={styles.value}>
      <SymbolView name={CALENDAR} size={18} tintColor={colors.textMuted} />
      <View style={styles.text} aria-live="polite">
        {value === '' ? (
          <AppText tone="muted" numberOfLines={1}>
            {NO_DATE}
          </AppText>
        ) : date === null ? (
          <AppText numberOfLines={1}>{value}</AppText>
        ) : (
          <AppText numberOfLines={1}>
            {relative ? (
              <>
                {relative}
                <AppText tone="muted">{`  ${formatFieldDay(date, today)}`}</AppText>
              </>
            ) : (
              formatFieldDay(date, today)
            )}
          </AppText>
        )}
      </View>
      {trailing ? <SymbolView name={trailing} size={20} tintColor={colors.textMuted} /> : null}
    </View>
  );
}

/** The box around a date field, as `TextField` and `SelectField` draw theirs. */
export const fieldBox = StyleSheet.create({
  box: { borderRadius: RADIUS.md, borderWidth: 1.5, overflow: 'hidden' },
}).box;

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: SPACING.xs },
  label: { flex: 1 },
  chip: {
    minHeight: 26,
    justifyContent: 'center',
    paddingHorizontal: SPACING.sm + 2,
    borderRadius: RADIUS.pill,
    borderWidth: 1.5,
  },
  chipText: { fontWeight: '600' },
  value: {
    minHeight: FIELD_INNER_HEIGHT,
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
    paddingHorizontal: SPACING.md,
  },
  text: { flex: 1 },
});
