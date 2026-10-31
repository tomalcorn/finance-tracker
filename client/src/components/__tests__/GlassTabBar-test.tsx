import { fireEvent, render, screen } from '@testing-library/react-native';

import { GlassTabBar, tabBarClearance, type GlassTabItem } from '@/components/GlassTabBar';

const TABS: GlassTabItem[] = [
  { key: 'home', label: 'Home', icon: { ios: 'house', web: 'home' } },
  { key: 'settings', label: 'Settings', icon: { ios: 'gearshape', web: 'settings' } },
];

describe('GlassTabBar', () => {
  it('marks the selected tab as selected', async () => {
    await render(<GlassTabBar items={TABS} selectedKey="settings" onSelect={() => {}} />);

    expect(screen.getByRole('tab', { name: 'Settings' })).toBeSelected();
  });

  it('reports the key of a pressed tab', async () => {
    const onSelect = jest.fn();
    await render(<GlassTabBar items={TABS} selectedKey="home" onSelect={onSelect} />);

    await fireEvent.press(screen.getByRole('tab', { name: 'Settings' }));

    expect(onSelect).toHaveBeenCalledWith('settings');
  });
});

describe('tabBarClearance', () => {
  it('keeps the bar clear of the bottom edge on a screen with no inset', () => {
    expect(tabBarClearance(0)).toBeGreaterThan(64);
  });

  it('grows with the bottom safe-area inset', () => {
    expect(tabBarClearance(34)).toBeGreaterThan(tabBarClearance(0));
  });
});
