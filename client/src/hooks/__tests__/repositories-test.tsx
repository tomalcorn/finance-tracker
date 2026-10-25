import { renderHook } from '@testing-library/react-native';

import { MissingProviderError } from '@/hooks/MissingProviderError';
import { useRepositories } from '@/hooks/repositories';

afterEach(() => {
  jest.restoreAllMocks();
});

describe('useRepositories', () => {
  it('names the provider it needs when used outside one', async () => {
    jest.spyOn(console, 'error').mockImplementation(() => {});

    await expect(renderHook(() => useRepositories())).rejects.toMatchObject({
      constructor: MissingProviderError,
      hook: 'useRepositories',
      provider: 'DataProvider',
    });
  });
});
