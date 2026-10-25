/** A hook was used outside the provider that supplies what it reads. */
export class MissingProviderError extends Error {
  readonly hook: string;
  readonly provider: string;

  constructor(hook: string, provider: string) {
    super(`${hook} must be used inside a ${provider}.`);
    this.name = 'MissingProviderError';
    this.hook = hook;
    this.provider = provider;
  }
}
