import type { CacheKey } from '@/ports/repository';

/**
 * What a repository needs from the read cache: dropping the reads a write
 * changed. The repository decides which keys those are; the implementation is
 * supplied by composition.
 */
export interface CacheInvalidator {
  invalidate(keys: readonly CacheKey[]): Promise<void>;
}
