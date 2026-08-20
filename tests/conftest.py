"""Helper functions and fixtures for tests."""

import uuid
from collections.abc import Callable, Sequence
from typing import Any

import pydantic
import pytest
import streamlit as st
import streamlit.testing.v1 as st_test

from domain import entities
from ports import repository


@pytest.fixture(autouse=True)
def _clear_session_state() -> None:
    """Clear streamlit session state before each test."""
    st.session_state.clear()


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


# == Repository fake fixtures ==

_PAYMENT_ADAPTER = pydantic.TypeAdapter(entities.AnyPaymentModel)


class FakeRepository[E: pydantic.BaseModel](repository.Repository[E]):
    """In-memory ``Repository`` recording every write it is handed.

    Bound to ``pydantic.BaseModel`` rather than ``FinanceTrackerBaseModel``: the
    joint tables carry no ownership dimension, so their models are not
    ``FinanceTrackerBaseModel``. ``build_entities`` mirrors the real gate, merging
    ``context`` into each raw row before validating with ``parse``.
    """

    def __init__(
        self,
        items: "Sequence[E] | None" = None,
        *,
        parse: "Callable[[entities.RawRow], E] | None" = None,
        context: "entities.RawRow | None" = None,
    ) -> None:
        """Seed the fake, optionally teaching it how to build entities."""
        self._items: list[E] = list(items or [])
        self._parse = parse
        self._context = dict(context or {})
        self.saved: list[E] = []
        self.built: list[entities.RawRow] = []
        self.edits: list[entities.EditedRows] = []
        self.deleted: list[str] = []
        self.save_error: Exception | None = None
        # The read counterpart of save_error: set it to make every read fail the
        # way a repository does at the port boundary.
        self.read_error: Exception | None = None

    def seed(self, *items: E) -> None:
        """Pre-load rows without recording them as saves."""
        self._items.extend(items)

    def get_all(self) -> list[E]:
        if self.read_error is not None:
            raise self.read_error
        return list(self._items)

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[E]:
        if self.read_error is not None:
            raise self.read_error
        wanted = {str(i) for i in ids}
        return [item for item in self._items if str(getattr(item, "id", "")) in wanted]

    def get_by_id(self, item_id: uuid.UUID) -> E | None:
        """Return the stored row with this id, if any (test-only convenience)."""
        return next(iter(self.get_by_ids([item_id])), None)

    def build_entities(self, rows: "Sequence[entities.RawRow]") -> list[E]:
        self.built.extend(rows)
        if self._parse is None:
            raise NotImplementedError
        return [self._parse({**row, **self._context}) for row in rows]

    def save_entities(self, items: "Sequence[E]") -> None:
        if self.save_error is not None:
            raise self.save_error
        for item in items:
            # An upsert: a saved copy replaces the stored row of the same id.
            self._items = [
                stored
                for stored in self._items
                if getattr(stored, "id", None) != getattr(item, "id", None)
            ]
            self._items.append(item)
            self.saved.append(item)

    def apply_edits(self, edits: "entities.EditedRows") -> None:
        if edits:
            self.edits.append(edits)

    def apply_deletions(self, ids: "entities.DeletedIds") -> None:
        self.deleted.extend(ids)


class StubDataSource[ViewT: pydantic.BaseModel]:
    """``GridDataSource`` stub: fixed reads, recording every write.

    Generic over the view model it answers with, so it satisfies a concretely
    parameterised ``GridDataSource[…]`` the way a repository does.

    ``model`` teaches the stub how to build entities; omit it for a test that
    never drives the create path.
    """

    def __init__(
        self,
        rows: "Sequence[ViewT] | None" = None,
        column_values: set[object] | None = None,
        model: type[pydantic.BaseModel] | None = None,
        context: "entities.RawRow | None" = None,
    ) -> None:
        """Fix the reads this stub answers and prepare the write records."""
        self._rows: list[ViewT] = list(rows or [])
        self._column_values = column_values or set()
        self._model = model
        self._context = dict(context or {})
        self.built: list[entities.RawRow] = []
        self.saved: list[pydantic.BaseModel] = []
        self.edits: list[entities.EditedRows] = []
        self.deleted: list[str] = []

    def rows(self) -> list[ViewT]:
        return list(self._rows)

    # column_name is unused: the stub answers one fixed value set.
    def unique_values(self, column_name: str) -> set[object]:  # noqa: ARG002
        return self._column_values

    def build_entities(
        self,
        rows: "Sequence[entities.RawRow]",
    ) -> list[pydantic.BaseModel]:
        self.built.extend(rows)
        if self._model is None:
            raise NotImplementedError
        return [self._model.model_validate({**row, **self._context}) for row in rows]

    def save_entities(self, items: "Sequence[pydantic.BaseModel]") -> None:
        self.saved.extend(items)

    def apply_edits(self, edits: "entities.EditedRows") -> None:
        if edits:
            self.edits.append(edits)

    def apply_deletions(self, ids: "entities.DeletedIds") -> None:
        self.deleted.extend(ids)


type RepoBuilder = Callable[..., FakeRepository[Any]]
type PaymentRepoBuilder = Callable[..., FakeRepository[entities.AnyPaymentModel]]
type StubDataSourceBuilder = Callable[..., StubDataSource[Any]]


@pytest.fixture(name="build_repo")
def _build_repo() -> "RepoBuilder":
    """Return a builder for an in-memory repository fake.

    A test overrides only what it varies — seeded rows, the parser the gate uses,
    the context that parser completes rows with — and inherits the rest.
    """

    def _build(
        items: "Sequence[Any] | None" = None,
        *,
        parse: "Callable[[entities.RawRow], Any] | None" = None,
        context: "entities.RawRow | None" = None,
    ) -> "FakeRepository[Any]":
        return FakeRepository(items, parse=parse, context=context)

    return _build


@pytest.fixture(name="build_payment_repo")
def _build_payment_repo() -> "PaymentRepoBuilder":
    """Return a builder for a payments fake whose gate parses the union.

    Payments are the one aggregate without a single write model, so a fake that
    builds them needs the union's ``TypeAdapter`` rather than one model's
    ``model_validate``.
    """

    def _build(
        user_id: str,
        items: "Sequence[entities.AnyPaymentModel] | None" = None,
        *,
        context: "entities.RawRow | None" = None,
    ) -> "FakeRepository[entities.AnyPaymentModel]":
        return FakeRepository(
            items,
            parse=_PAYMENT_ADAPTER.validate_python,
            # context adds to the owner every payments repo writes under, so a
            # joint-mode fake can carry the ownership its gate stamps on.
            context={"user_id": user_id, **(context or {})},
        )

    return _build


@pytest.fixture(name="build_stub_data_source")
def _build_stub_data_source() -> "StubDataSourceBuilder":
    """Return a builder for the grid data-source stub."""

    def _build(
        rows: "Sequence[Any] | None" = None,
        column_values: set[object] | None = None,
        model: type[pydantic.BaseModel] | None = None,
        context: "entities.RawRow | None" = None,
    ) -> "StubDataSource[Any]":
        return StubDataSource(rows, column_values, model, context)

    return _build


# == Pages fixtures ==


# Can't type docs_dir, doesn't work with AppTest
def _docs_pages_app(docs_dir, *, render_boom: bool = False) -> None:  # noqa: ANN001
    from unittest import mock

    import streamlit as st

    from driving_adapters.pages import docs_pages

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
