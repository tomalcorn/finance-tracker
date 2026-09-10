"""Unit tests for the keep-awake visit's configuration and origin check."""

import pytest

from ops import keep_awake

_APP_URL = "https://finance-tracker.streamlit.app"
_AUTH0_URL = "https://example.eu.auth0.com/authorize?client_id=abc"


class TestResolveAppUrl:
    """Tests for resolve_app_url."""

    def test_returns_the_configured_url(self) -> None:
        # Act
        url = keep_awake.resolve_app_url({keep_awake.APP_URL_VARIABLE: _APP_URL})
        # Assert
        assert url == _APP_URL

    def test_strips_surrounding_whitespace(self) -> None:
        # Act
        url = keep_awake.resolve_app_url(
            {keep_awake.APP_URL_VARIABLE: f"  {_APP_URL}\n"},
        )
        # Assert
        assert url == _APP_URL

    def test_missing_variable_names_the_variable(self) -> None:
        # Act / Assert
        with pytest.raises(keep_awake.MissingAppUrlError) as exc_info:
            keep_awake.resolve_app_url({})
        assert exc_info.value.variable == keep_awake.APP_URL_VARIABLE

    def test_blank_variable_is_treated_as_missing(self) -> None:
        # A repository variable that exists but was never filled in reads as an
        # empty string, which would otherwise send the browser to about:blank.
        # Act / Assert
        with pytest.raises(keep_awake.MissingAppUrlError):
            keep_awake.resolve_app_url({keep_awake.APP_URL_VARIABLE: "   "})


class TestHasLeftOrigin:
    """Tests for has_left_origin."""

    def test_redirect_to_the_identity_provider_has_left(self) -> None:
        # Act / Assert
        assert keep_awake.has_left_origin(_AUTH0_URL, _APP_URL)

    def test_the_app_itself_has_not_left(self) -> None:
        # Act / Assert
        assert not keep_awake.has_left_origin(_APP_URL, _APP_URL)

    def test_a_path_on_the_app_has_not_left(self) -> None:
        # The sleeping page and the app's own pages share the app's host, so
        # neither may be mistaken for the redirect that proves the app ran.
        # Act / Assert
        assert not keep_awake.has_left_origin(f"{_APP_URL}/~/+/", _APP_URL)
