import { act, renderHook } from '@testing-library/react-native';

import { messageOf, useSubmit } from '@/hooks/submit';

/** A promise that never settles, for an action still under way. */
function pending(): Promise<void> {
  return new Promise(() => {});
}

describe('messageOf', () => {
  it('reads an error’s message', () => {
    expect(messageOf(new Error('Network down'))).toBe('Network down');
  });

  it('reads anything else as text', () => {
    expect(messageOf(404)).toBe('404');
  });
});

describe('useSubmit', () => {
  it('runs the action with what it is given', async () => {
    const action = jest.fn((_name: string, _count: number) => Promise.resolve());
    const { result } = await renderHook(() => useSubmit(action));

    await act(() => result.current.submit('draft', 2));

    expect(action).toHaveBeenCalledWith('draft', 2);
  });

  it('is saving while the action runs', async () => {
    const { result } = await renderHook(() => useSubmit(pending));

    await act(async () => {
      void result.current.submit();
    });

    expect(result.current.saving).toBe(true);
  });

  it('stops saving once the action succeeds', async () => {
    const { result } = await renderHook(() => useSubmit(() => Promise.resolve()));

    await act(() => result.current.submit());

    expect(result.current.saving).toBe(false);
  });

  it('keeps saving after a success when the form is used once', async () => {
    const { result } = await renderHook(() => useSubmit(() => Promise.resolve(), { once: true }));

    await act(() => result.current.submit());

    expect(result.current.saving).toBe(true);
  });

  it('stops saving after a failure, even when the form is used once', async () => {
    const { result } = await renderHook(() =>
      useSubmit(() => Promise.reject(new Error('Network down')), { once: true }),
    );

    await act(() => result.current.submit());

    expect(result.current.saving).toBe(false);
  });

  it('keeps the failure’s message', async () => {
    const { result } = await renderHook(() =>
      useSubmit(() => Promise.reject(new Error('Network down'))),
    );

    await act(() => result.current.submit());

    expect(result.current.failure).toBe('Network down');
  });

  it('clears the last failure when it runs again', async () => {
    const action = jest
      .fn<Promise<void>, []>()
      .mockRejectedValueOnce(new Error('Network down'))
      .mockReturnValueOnce(pending());
    const { result } = await renderHook(() => useSubmit(action));
    await act(() => result.current.submit());

    await act(async () => {
      void result.current.submit();
    });

    expect(result.current.failure).toBeNull();
  });

  it('clears the failure when asked', async () => {
    const { result } = await renderHook(() =>
      useSubmit(() => Promise.reject(new Error('Network down'))),
    );
    await act(() => result.current.submit());

    await act(async () => result.current.clearFailure());

    expect(result.current.failure).toBeNull();
  });
});
