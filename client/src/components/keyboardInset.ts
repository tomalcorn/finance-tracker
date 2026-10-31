import { useEffect, useState } from 'react';
import { Platform } from 'react-native';

/**
 * How much of the bottom of the window the on-screen keyboard covers, on the web. iOS Safari
 * shrinks only the visual viewport when the keyboard opens, so anything pinned to the bottom of
 * the page would sit behind it. Always 0 on native, where `KeyboardAvoidingView` does this job.
 */
export function useKeyboardInset(): number {
  const [inset, setInset] = useState(0);

  useEffect(() => {
    const viewport = Platform.OS === 'web' ? window.visualViewport : null;
    if (!viewport) return;
    const update = () =>
      setInset(Math.max(window.innerHeight - viewport.height - viewport.offsetTop, 0));
    viewport.addEventListener('resize', update);
    viewport.addEventListener('scroll', update);
    return () => {
      viewport.removeEventListener('resize', update);
      viewport.removeEventListener('scroll', update);
    };
  }, []);

  return inset;
}
