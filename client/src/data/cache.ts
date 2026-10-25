import type { CacheKey } from '@/ports/repository';

/**
 * What a repository needs from the read cache: a way to mark cached reads as
 * out of date after it writes. The repository decides which reads; composition
 * supplies the implementation.
 */
export interface CacheInvalidator {
  invalidate(keys: readonly CacheKey[]): Promise<void>;
}
