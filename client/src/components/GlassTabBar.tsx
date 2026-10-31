import { SymbolView, type SymbolViewProps } from 'expo-symbols';
import { createContext, useContext, useEffect, useState } from 'react';
import { Animated, Platform, Pressable, StyleSheet, View, type ViewStyle } from 'react-native';

import { AppText } from '@/components/AppText';
import { useAppTheme } from '@/theme/theme';
import { RADIUS, SPACING } from '@/theme/tokens';

export type GlassTabItem = {
  key: string;
  label: string;
  icon: SymbolViewProps['name'];
};

type GlassTabBarProps = {
  items: readonly GlassTabItem[];
  selectedKey: string;
  onSelect: (key: string) => void;
  /** The device's bottom safe-area inset, which the floating bar sits clear of. */
  bottomInset?: number;
  /** Float the bar over the bottom of the screen. Off, it sits in the layout like any view. */
  floating?: boolean;
};

const BAR_HEIGHT = 64;
const BAR_PADDING = 6;
const MAX_BAR_WIDTH = 420;

/** How far above the bottom edge the floating bar sits, given the bottom safe-area inset. */
function barOffset(bottomInset: number): number {
  return Math.max(bottomInset - SPACING.md, SPACING.md);
}

/** The space a screen leaves below its content so the floating bar never covers it. */
export function tabBarClearance(bottomInset: number): number {
  return barOffset(bottomInset) + BAR_HEIGHT;
}

/** The space below a screen's content taken by a floating tab bar, or 0 outside the tabs. */
export const TabBarClearanceContext = createContext(0);

export function useTabBarClearance(): number {
  return useContext(TabBarClearanceContext);
}

// React Native has no backdrop filter, so on the web the blur is passed through as raw CSS, which
// react-native-web forwards to the element. Without it the bar is still translucent, just not frosted.
const BLUR = Platform.select<ViewStyle>({
  web: {
    backdropFilter: 'blur(24px) saturate(180%)',
    WebkitBackdropFilter: 'blur(24px) saturate(180%)',
  } as ViewStyle,
  default: {},
});

const SHADOW = {
  light: '0 10px 30px rgba(28, 27, 25, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.7)',
  dark: '0 10px 30px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.08)',
};

/** A floating, frosted-glass pill of tabs, each an icon over a label, with a sliding highlight. */
export function GlassTabBar({
  items,
  selectedKey,
  onSelect,
  bottomInset = 0,
  floating = true,
}: GlassTabBarProps) {
  const { dark, colors } = useAppTheme();
  const [width, setWidth] = useState(0);
  const selectedIndex = Math.max(
    items.findIndex((item) => item.key === selectedKey),
    0,
  );
  const tabWidth = width > 0 ? (width - BAR_PADDING * 2) / items.length : 0;
  const [position] = useState(() => new Animated.Value(selectedIndex));

  useEffect(() => {
    Animated.spring(position, {
      toValue: selectedIndex,
      useNativeDriver: Platform.OS !== 'web',
      speed: 20,
      bounciness: 6,
    }).start();
  }, [position, selectedIndex]);

  return (
    <View
      pointerEvents="box-none"
      style={[styles.dock, floating && [styles.floating, { bottom: barOffset(bottomInset) }]]}
    >
      <View
        role="tablist"
        onLayout={(event) => setWidth(event.nativeEvent.layout.width)}
        style={[
          styles.bar,
          BLUR,
          {
            backgroundColor: colors.glass,
            borderColor: colors.glassBorder,
            boxShadow: dark ? SHADOW.dark : SHADOW.light,
          },
        ]}
      >
        {tabWidth > 0 ? (
          <Animated.View
            pointerEvents="none"
            style={[
              styles.highlight,
              {
                width: tabWidth,
                backgroundColor: colors.accentSoft,
                transform: [{ translateX: Animated.multiply(position, tabWidth) }],
              },
            ]}
          />
        ) : null}
        {items.map((item) => {
          const selected = item.key === selectedKey;
          const tint = selected ? colors.accent : colors.textMuted;
          return (
            <Pressable
              key={item.key}
              role="tab"
              aria-selected={selected}
              aria-label={item.label}
              onPress={() => onSelect(item.key)}
              style={({ pressed }) => [styles.tab, pressed && styles.pressed]}
            >
              <SymbolView name={item.icon} size={22} tintColor={tint} />
              <AppText numberOfLines={1} style={[styles.label, { color: tint }]}>
                {item.label}
              </AppText>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  dock: { alignItems: 'center', paddingHorizontal: SPACING.lg },
  floating: { position: 'absolute', left: 0, right: 0 },
  bar: {
    width: '100%',
    maxWidth: MAX_BAR_WIDTH,
    height: BAR_HEIGHT,
    flexDirection: 'row',
    padding: BAR_PADDING,
    borderRadius: RADIUS.pill,
    borderWidth: StyleSheet.hairlineWidth,
  },
  highlight: {
    position: 'absolute',
    top: BAR_PADDING,
    bottom: BAR_PADDING,
    left: BAR_PADDING,
    borderRadius: RADIUS.pill,
  },
  tab: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 2 },
  label: { fontSize: 11, lineHeight: 14, fontWeight: '600' },
  pressed: { opacity: 0.6 },
});
