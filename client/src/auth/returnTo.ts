/**
 * `returnTo` if it is a path inside the app, otherwise `/`.
 *
 * Accepts only a single leading slash: an href with a scheme is opened as an
 * external link, and browsers read `//host` and `/\host` as another origin.
 */
export function safeReturnTo(returnTo: string | null | undefined): string {
  return returnTo && /^\/(?![/\\])/.test(returnTo) ? returnTo : '/';
}
