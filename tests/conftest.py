"""Helper functions and fixtures for tests."""

import typing
import uuid
from collections.abc import Callable
from typing import Any

import pandas as pd
import pydantic
import pytest
import st_supabase_connection
import streamlit as st
import streamlit.testing.v1 as st_test

from domain import entities, query
from ui.components.dfes import base_dfe
from ui.models import frontend_models


@pytest.fixture(autouse=True)
def _clear_session_state() -> None:
    """Clear streamlit session state before each test."""
    st.session_state.clear()


@pytest.fixture(name="connection")
def _connection() -> st_supabase_connection.SupabaseConnection:
    """Provide a Supabase connection for tests."""
    return st.connection(
        "testing",
        type=st_supabase_connection.SupabaseConnection,
    )


@pytest.fixture(name="sample_bank_account")
def _sample_bank_account() -> entities.BankAccountModel:
    """Provide a sample bank account model for tests."""
    return entities.BankAccountModel(
        user_id="auth0|test-user-1",
        name="Test Account 1",
        starting_balance=100.0,
    )


@pytest.fixture(name="yield_sample_bank_account")
def _yield_sample_bank_account(
    connection: st_supabase_connection.SupabaseConnection,
    sample_bank_account: entities.BankAccountModel,
) -> typing.Generator[entities.BankAccountModel, None, None]:
    """Set up a sample bank account for tests."""
    connection.table("bank_accounts").insert(
        sample_bank_account.model_dump(mode="json"),
    ).execute()

    yield sample_bank_account

    # Clean up the bank account from the test database
    connection.table("bank_accounts").delete().eq(
        "id",
        str(sample_bank_account.id),
    ).execute()


@pytest.fixture(name="yield_sample_bank_accounts")
def _yield_sample_bank_accounts(
    sample_bank_account: entities.BankAccountModel,
    connection: st_supabase_connection.SupabaseConnection,
) -> typing.Generator[list[entities.BankAccountModel], None, None]:
    """Set up multiple sample bank accounts for tests."""
    sample_bank_accounts = [
        sample_bank_account,
        sample_bank_account.model_copy(
            update={"id": uuid.uuid4(), "name": "Test Account 2"},
            deep=True,
        ),
    ]
    # Insert bank accounts into the test database
    for account in sample_bank_accounts:
        connection.table("bank_accounts").insert(
            account.model_dump(mode="json"),
        ).execute()

    yield sample_bank_accounts

    # Clean up the bank accounts from the test database
    for account in sample_bank_accounts:
        connection.table("bank_accounts").delete().eq(
            "id",
            str(account.id),
        ).execute()


def get_rendered_texts(app_tester: st_test.AppTest) -> list[str]:
    """Get all rendered texts from the app tester.

    Args:
        app_tester: The Streamlit app tester instance.

    Returns:
        A list of rendered texts.

    """
    texts = [t.value for t in getattr(app_tester, "text", [])]
    markdowns = [m.value for m in getattr(app_tester, "markdown", [])]
    return texts + markdowns


@pytest.fixture(name="col_configs")
def _col_configs() -> list[frontend_models.DFEColumnConfigBase]:
    return [
        frontend_models.DFEColumnConfigBase(
            column_name="col1",
            column_config={},
            input_widget=st.text_input,
            sorting=query.SortingValues.ASC,
            filters=query.Filters(lte="2023-01-01", gte="2022-01-01"),
        ),
    ]


# == Pages fixtures ==


# Can't type docs_dir, doesn't work with AppTest
def _docs_pages_app(docs_dir, *, render_boom: bool = False) -> None:  # noqa: ANN001
    from unittest import mock

    import streamlit as st

    from ui.pages import docs_pages

    registry = docs_pages.DocsRegistry(docs_dir)
    pages = docs_pages.DocsUI(registry).build_pages()
    st.json(
        [
            {
                "title": page.title,
                "icon": page.icon,
                "url_path": page.url_path,
            }
            for page in pages
        ],
    )

    if render_boom:
        with mock.patch("streamlit.markdown", side_effect=RuntimeError("render boom")):
            st.navigation(pages).run()
        return

    st.navigation(pages).run()


@pytest.fixture(name="app_tester_getter")
def _app_tester_getter() -> Callable[..., st_test.AppTest]:

    def _app_tester(**kwargs: dict[str, Any]) -> st_test.AppTest:
        return st_test.AppTest.from_function(
            _docs_pages_app,
            default_timeout=120,
            kwargs=kwargs,
        )

    return _app_tester


# == DFE fixtures ==


class _StubModel(pydantic.BaseModel):
    pass


@pytest.fixture(name="dfe_instance")
def _dfe_instance(
    col_configs: list[frontend_models.DFEColumnConfigBase],
) -> base_dfe.DFE:
    """Fixture for a DFE instance with sample user data."""
    return base_dfe.DFE(
        config=frontend_models.DFEConfig(
            table_names=frontend_models.DFETableNameConfig(
                write_table="bank_accounts",
            ),
            backend_model=_StubModel,
            configs=col_configs,
            sample_data=pd.DataFrame(),
        ),
    )


# == auth fixtures ==


@pytest.fixture(autouse=True, scope="module")
def _clean_bank_accounts_table() -> None:
    """Remove any rows left over from a previous failed test run."""
    connection: st_supabase_connection.SupabaseConnection = st.connection(
        "testing",
        type=st_supabase_connection.SupabaseConnection,
    )
    connection.table("bank_accounts").delete().neq(
        "id",
        "00000000-0000-0000-0000-000000000000",
    ).execute()
