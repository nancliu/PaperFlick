"""Domain primitives for Print Items and Batch lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, assert_never
from uuid import UUID, uuid4

if TYPE_CHECKING:
    from paperflick.core.batch.formats import DocKind, Probe


class Orientation(Enum):
    """Page orientation policy for one Print Item."""

    AUTO = "auto"
    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"
    PRINTER_DEFAULT = "printer_default"


class Facing(Enum):
    """A resolved page direction. Not a policy, so it cannot be stored as Orientation."""

    LANDSCAPE = "landscape"
    PORTRAIT = "portrait"


@dataclass(frozen=True, slots=True)
class Measured:
    """First-page size as displayed, in one consistent unit for that file."""

    width: float
    height: float


@dataclass(frozen=True, slots=True)
class Unread:
    """The first page could not be measured. Auto resolves this to portrait."""

    reason: str


PageShape = Measured | Unread


def resolve_facing(policy: Orientation, shape: PageShape) -> Facing | None:
    """Turn a policy and a page fact into a direction.

    None means leave the direction to the printer. Auto treats a wider page as
    landscape. A square page and an unread file are portrait. Forced landscape
    or portrait ignore the fact.
    """
    if policy is Orientation.PRINTER_DEFAULT:
        return None
    if policy is Orientation.LANDSCAPE:
        return Facing.LANDSCAPE
    if policy is Orientation.PORTRAIT:
        return Facing.PORTRAIT
    if policy is not Orientation.AUTO:
        assert_never(policy)
    if isinstance(shape, Measured):
        if shape.width > shape.height:
            return Facing.LANDSCAPE
        return Facing.PORTRAIT
    if isinstance(shape, Unread):
        return Facing.PORTRAIT
    assert_never(shape)


class ItemStatus(Enum):
    """Lifecycle of one Print Item inside a Batch."""

    WAITING = "waiting"
    PRINTING = "printing"
    SUCCESS = "success"
    FAILED = "failed"


class BatchPhase(Enum):
    """Whether a Batch is idle or advancing."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass(frozen=True, slots=True)
class ItemId:
    """Opaque id for one Print Item row."""

    value: UUID


@dataclass(frozen=True, slots=True)
class PrintItem:
    """One row in the Batch list.

    ``orientation`` is the user's policy. ``shape`` is the file fact read once
    at add time. The resolved direction is never stored on the row.
    """

    id: ItemId
    path: Path
    kind: DocKind
    shape: PageShape
    orientation: Orientation
    status: ItemStatus
    failure_reason: str | None = None

    @classmethod
    def added(cls, path: Path, probed: Probe) -> PrintItem:
        """Build a newly added row. Policy is Auto and status is Waiting.

        There is no orientation argument, so a prior bulk override cannot be
        passed in.
        """
        return cls(
            id=ItemId(uuid4()),
            path=path,
            kind=probed.kind,
            shape=probed.shape,
            orientation=Orientation.AUTO,
            status=ItemStatus.WAITING,
        )
