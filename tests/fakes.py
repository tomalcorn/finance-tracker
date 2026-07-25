"""Shared in-memory test doubles for the repository port.

One fake implements the whole write contract, so a test can assert on what was
built, saved, patched, or deleted without a backend. Kept here rather than
duplicated per test module because every use-case test needs the same shape.
"""

import uuid
from typing import TYPE_CHECKING

import pydantic

from domain import entities
from ports import errors as port_errors
from ports import repository

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_PAYMENT_ADAPTER = pydantic.TypeAdapter(entities.AnyPaymentModel)


class FakeRepository[E: pydantic.BaseModel](repository.Repository[E]):
    """In-memory ``Repository`` recording every write it is handed.

    Bound to ``pydantic.BaseModel`` rather than ``FinanceTrackerBaseModel``: the
    joint tables carry no user/ownership dimension, so their models are not
    ``FinanceTrackerBaseModel``.

    ``build_entities`` mirrors the real gate — it merges ``context`` into each
    raw row and validates with ``parse`` — so a test exercising a create path
    sees the same completion the Supabase repository would apply.
    """

    def __init__(
        self,
        items: "Sequence[E] | None" = None,
        *,
        parse: "Callable[[entities.RawRow], E] | None" = None,
        context: "entities.RawRow | None" = None,
    ) -> None:
        """Seed the fake, optionally teaching it how to build entities.

        Args:
            items: Rows already stored, as if previously persisted.
            parse: Validator used by ``build_entities``; omit for a repository
                whose create path the test never drives.
            context: Fields ``build_entities`` merges into every raw row,
                standing in for the real write context.

        """
        self._items: list[E] = list(items or [])
        self._parse = parse
        self._context = dict(context or {})
        self.saved: list[E] = []
        self.built: list[entities.RawRow] = []
        self.edits: list[entities.EditedRows] = []
        self.deleted: list[str] = []
        self.save_error: Exception | None = None

    def seed(self, *items: E) -> None:
        """Pre-load rows without recording them as saves."""
        self._items.extend(items)

    def get_all(self) -> list[E]:
        return list(self._items)

    def get_by_ids(self, ids: list[uuid.UUID]) -> list[E]:
        wanted = {str(i) for i in ids}
        return [item for item in self._items if str(getattr(item, "id", "")) in wanted]

    def get_by_id(self, item_id: uuid.UUID) -> E | None:
        """Return the row with this id, if stored.

        A test-only convenience (not on the port): entities are frozen, so a test
        checking an update has to look the stored copy back up rather than
        inspecting the object it passed in.
        """
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


class FailingRepository[E: pydantic.BaseModel](FakeRepository[E]):
    """Repository fake whose whole-entity writes fail at the port boundary."""

    # items is unused: the fake exists only to fail at the port boundary.
    def save_entities(self, items: "Sequence[E]") -> None:  # noqa: ARG002
        msg = "backend unavailable"
        raise port_errors.RepositoryError(msg)


class StubDataSource:
    """``GridDataSource`` stub: fixed reads, recording every write.

    Mirrors the repository's split write surface so a grid test can assert what
    was created, patched, or deleted. ``model`` teaches the stub how to build
    entities; omit it for a test that never drives the create path.
    """

    def __init__(
        self,
        rows: "Sequence[pydantic.BaseModel] | None" = None,
        column_values: set[object] | None = None,
        model: type[pydantic.BaseModel] | None = None,
        context: "entities.RawRow | None" = None,
    ) -> None:
        """Fix the reads this stub answers and prepare the write records."""
        self._rows = list(rows or [])
        self._column_values = column_values or set()
        self._model = model
        self._context = dict(context or {})
        self.built: list[entities.RawRow] = []
        self.saved: list[pydantic.BaseModel] = []
        self.edits: list[entities.EditedRows] = []
        self.deleted: list[str] = []

    def rows(self) -> list[pydantic.BaseModel]:
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


def payment_fake(
    user_id: str,
    items: "Sequence[entities.AnyPaymentModel] | None" = None,
) -> FakeRepository[entities.AnyPaymentModel]:
    """Return a payments fake whose gate parses the discriminated union.

    Payments are the one aggregate without a single write model, so a fake that
    has to build them needs the union's ``TypeAdapter`` rather than one model's
    ``model_validate``.
    """
    return FakeRepository(
        items,
        parse=_PAYMENT_ADAPTER.validate_python,
        context={"user_id": user_id},
    )
