/** Base class for errors raised across a persistence port. */
export class PortError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = new.target.name;
  }
}

/** A repository could not read or write its aggregate. */
export class RepositoryError extends PortError {}

/** A field and what is wrong with it. */
export type RowIssue = { field: string; message: string };

/** A row failed its schema, on its way in through `build` or out of a read. */
export class InvalidRowError extends RepositoryError {
  readonly table: string;
  readonly issues: readonly RowIssue[];

  constructor(table: string, issues: readonly RowIssue[], options?: { cause?: unknown }) {
    const detail = issues.map(({ field, message }) => `${field}: ${message}`).join('; ');
    super(`Invalid row for ${table}: ${detail}`, options);
    this.table = table;
    this.issues = issues;
  }
}

/** A joint repository was used by a user who belongs to no joint account. */
export class NoJointAccountError extends RepositoryError {
  readonly userId: string;

  constructor(userId: string) {
    super(`User ${userId} belongs to no joint account.`);
    this.userId = userId;
  }
}
