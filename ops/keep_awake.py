"""Visit the deployed app so Community Cloud does not put it to sleep.

Streamlit Community Cloud hibernates an app after 12 hours without traffic, and
its traffic counter follows real browser sessions rather than plain HTTP
requests: a ``curl`` against a sleeping app returns 200 while the app stays
asleep. So this visits the app the way a person does — a headless browser that
opens the same websocket a real visitor opens — and clicks Community Cloud's
"get this app back up" button when the app has already gone to sleep.

The visit never signs in, and needs no credentials. ``streamlit_app.py`` sends
an anonymous visitor straight to Auth0, and landing there is proof enough that
the app woke: the app script has to run to reach the redirect, and running is
what resets the hibernation timer.

Run on a schedule by ``.github/workflows/keep-awake.yml``; see the README for
the repository variable it reads.
"""

import argparse
import os
import pathlib
import re
import sys
import time
import urllib.parse
from typing import TYPE_CHECKING

from playwright import sync_api

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

APP_URL_VARIABLE = "STREAMLIT_APP_URL"

# Community Cloud's sleeping page offers a single button to boot the app. Match
# it loosely: the surrounding copy has been reworded before now, "get this app
# back up" has not.
_WAKE_BUTTON = re.compile("get this app back up", re.IGNORECASE)
_APP_ROOT = "[data-testid='stApp']"

_DEFAULT_TIMEOUT_SECONDS = 180.0
_NAVIGATION_TIMEOUT_MS = 60_000
_POLL_INTERVAL_MS = 2_000

_EXIT_OK = 0
_EXIT_FAILED = 1
_EXIT_MISCONFIGURED = 2


class KeepAwakeError(Exception):
    """Base class for all keep-awake errors."""


class MissingAppUrlError(KeepAwakeError):
    """Raised when no app URL is configured for the visit."""

    def __init__(self, variable: str) -> None:
        """Construct MissingAppUrlError.

        Args:
            variable: The environment variable expected to hold the app URL.

        """
        self.variable = variable
        super().__init__(
            f"No Streamlit app URL configured; set the {variable} repository "
            f"variable, or pass --url.",
        )


class AppUnreachableError(KeepAwakeError):
    """Raised when the app neither rendered nor redirected before the deadline."""

    def __init__(self, url: str, timeout_seconds: float) -> None:
        """Construct AppUnreachableError.

        Args:
            url: The app URL that was visited.
            timeout_seconds: How long the visit waited before giving up.

        """
        self.url = url
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"{url} neither rendered nor redirected within "
            f"{timeout_seconds:.0f}s; the app may be failing to boot.",
        )


def resolve_app_url(environ: "Mapping[str, str]") -> str:
    """Return the app URL configured in the environment.

    Args:
        environ: The environment to read ``STREAMLIT_APP_URL`` from.

    Returns:
        The configured URL, stripped of surrounding whitespace.

    Raises:
        MissingAppUrlError: the variable is unset or blank.

    """
    url = environ.get(APP_URL_VARIABLE, "").strip()
    if not url:
        raise MissingAppUrlError(APP_URL_VARIABLE)
    return url


def has_left_origin(current_url: str, app_url: str) -> bool:
    """Report whether the browser has navigated off the app's own host.

    Leaving is the signal that the app ran: an anonymous visitor is redirected
    to Auth0, which only happens once ``streamlit_app.py`` has executed.

    Args:
        current_url: Where the browser is now.
        app_url: The app URL the visit started from.

    Returns:
        True when the two URLs have different hosts.

    """
    return urllib.parse.urlsplit(current_url).netloc != (
        urllib.parse.urlsplit(app_url).netloc
    )


def _count(locator: "sync_api.Locator") -> int:
    """Count a locator's matches, reading a navigation in flight as no match.

    Args:
        locator: The locator to count.

    Returns:
        The number of matching elements, or 0 if the page moved under us.

    """
    try:
        return locator.count()
    except sync_api.Error:
        return 0


def _click_wake_button(page: "sync_api.Page") -> bool:
    """Click the wake button if Community Cloud's sleeping page is showing.

    Args:
        page: The page showing either the app or the sleeping page.

    Returns:
        True if the app was asleep and the button was clicked.

    """
    button = page.get_by_role("button", name=_WAKE_BUTTON)
    if not _count(button):
        return False
    button.first.click()
    return True


def visit(page: "sync_api.Page", url: str, timeout_seconds: float) -> str:
    """Load the app and wait until its script has demonstrably run.

    Args:
        page: The browser page to visit with.
        url: The app URL.
        timeout_seconds: How long to wait for the app before giving up. Booting
            a sleeping app takes far longer than loading a warm one, so this
            covers a cold start rather than a page load.

    Returns:
        A short description of what ended the wait.

    Raises:
        AppUnreachableError: the deadline passed with the app still not running.

    """
    page.goto(url, wait_until="domcontentloaded", timeout=_NAVIGATION_TIMEOUT_MS)
    deadline = time.monotonic() + timeout_seconds
    woken = False
    while time.monotonic() < deadline:
        if has_left_origin(page.url, url):
            host = urllib.parse.urlsplit(page.url).netloc
            return f"redirected to {host}"
        if not woken and _click_wake_button(page):
            woken = True
            print("App was asleep; clicked the wake button and waited for boot.")
        elif _count(page.locator(_APP_ROOT)):
            return "app rendered"
        page.wait_for_timeout(_POLL_INTERVAL_MS)
    raise AppUnreachableError(url, timeout_seconds)


def _capture(page: "sync_api.Page", screenshot: pathlib.Path) -> None:
    """Save a screenshot for triage, ignoring a page too broken to photograph.

    Args:
        page: The page to photograph.
        screenshot: Where to write the PNG.

    """
    try:
        page.screenshot(path=screenshot)
    except sync_api.Error as error:
        print(f"Could not capture a screenshot: {error}", file=sys.stderr)


def _run(url: str, timeout_seconds: float, screenshot: pathlib.Path | None) -> int:
    """Open a browser, visit the app once, and report the outcome.

    Args:
        url: The app URL.
        timeout_seconds: How long to wait for the app before giving up.
        screenshot: Where to write a screenshot if the visit fails, if anywhere.

    Returns:
        A process exit code.

    """
    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        try:
            outcome = visit(page, url, timeout_seconds)
        except (KeepAwakeError, sync_api.Error) as error:
            if screenshot is not None:
                _capture(page, screenshot)
            print(f"Keep-awake visit failed: {error}", file=sys.stderr)
            return _EXIT_FAILED
        finally:
            browser.close()
    print(f"Visited {url}: {outcome}.")
    return _EXIT_OK


def main(argv: "Sequence[str] | None" = None) -> int:
    """Parse arguments and run a single keep-awake visit.

    Args:
        argv: Command-line arguments, defaulting to ``sys.argv``.

    Returns:
        A process exit code.

    """
    parser = argparse.ArgumentParser(
        description="Visit the deployed Streamlit app so it does not hibernate.",
    )
    parser.add_argument(
        "--url",
        default=None,
        help=f"App URL to visit. Defaults to ${APP_URL_VARIABLE}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=_DEFAULT_TIMEOUT_SECONDS,
        help="Seconds to wait for the app, including a cold boot.",
    )
    parser.add_argument(
        "--screenshot",
        type=pathlib.Path,
        default=None,
        help="Where to write a screenshot if the visit fails.",
    )
    args = parser.parse_args(argv)
    try:
        url = args.url or resolve_app_url(os.environ)
    except MissingAppUrlError as error:
        print(str(error), file=sys.stderr)
        return _EXIT_MISCONFIGURED
    return _run(url, args.timeout, args.screenshot)


if __name__ == "__main__":
    sys.exit(main())
