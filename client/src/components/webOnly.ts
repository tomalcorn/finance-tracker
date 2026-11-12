import { Platform, type View } from 'react-native';

/** A key press, as react-native-web hands it to `onKeyDown` and `onKeyUp`. */
export type KeyEvent = {
  key: string;
  shiftKey?: boolean;
  preventDefault: () => void;
  stopPropagation: () => void;
};

type WebProps = {
  /** A cell of a `grid`, which React Native's roles leave out. */
  role?: 'gridcell';
  onKeyDown?: (event: KeyEvent) => void;
  onKeyUp?: (event: KeyEvent) => void;
};

/**
 * Props that react-native-web's `View` passes on to the page and React Native's types leave out, to
 * spread into one: `<View {...webProps({ onKeyDown })} />`. The native build ignores them.
 */
export function webProps(props: WebProps): object {
  return props;
}

/** Moves keyboard focus onto a view. Only the web does: a phone has no focus to move. */
export function focusOnWeb(view: View | null): void {
  if (Platform.OS === 'web') view?.focus();
}

/** Scrolls whatever holds a view just far enough to show all of it. Only the web can. */
export function scrollIntoViewOnWeb(view: View | null): void {
  const element = view as { scrollIntoView?: (options: { block: 'nearest' }) => void } | null;
  if (Platform.OS === 'web') element?.scrollIntoView?.({ block: 'nearest' });
}
