import type { RawRow } from '@/domain/entities';

/** Identifies one cached read: what a screen's query is keyed by. */
export type CacheKey = readonly string[];

/**
 * Reads and writes one aggregate, in one ownership mode, for the signed-in user.
 *
 * Reads return view rows (`ViewT`), with the view's computed columns. Writes
 * take whole entities (`EntityT`), so every row written passes the entity's
 * schema first. To change a stored row, merge the change into its view row and
 * pass that back through `build`: a view row carries every writable column, and
 * `build` drops the computed ones.
 *
 * Every method throws `RepositoryError` on failure.
 */
export interface Repository<EntityT, ViewT> {
  /** The key this repository's `rows()` are cached under. */
  readonly cacheKey: CacheKey;

  /** Every row visible to the user in this repository's ownership mode. */
  rows(): Promise<ViewT[]>;

  /**
   * Complete raw rows with this repository's owner and ownership, then
   * validate them into entities: the write gate. The ownership fields always
   * come from the repository, never from the row. Nothing is written.
   *
   * @throws {InvalidRowError} when a row fails its entity's rules.
   * @throws {NoJointAccountError} when a joint repository's user has no joint account.
   */
  build(rows: readonly RawRow[]): Promise<EntityT[]>;

  /**
   * Insert or update each entity by id, then mark every cached read affected
   * by the write as out of date. An empty list does nothing.
   *
   * @throws {RepositoryError} when an entity is owned differently from this repository.
   */
  save(items: readonly EntityT[]): Promise<void>;

  /** Delete the rows with these ids, then invalidate what that changes. An empty list does nothing. */
  delete(ids: readonly string[]): Promise<void>;
}
