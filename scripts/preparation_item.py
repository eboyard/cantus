"""Une occurrence de chant ou de texte reste indivisible dans la préparation."""

from dataclasses import dataclass, field
from uuid import uuid4


@dataclass
class PreparationItem:
    path: str
    title: str
    moment: str = ""
    verses: list[str] | None = None
    uid: str = field(default_factory=lambda: uuid4().hex)

    def record(self) -> dict:
        return {"path": self.path, "moment": self.moment,
                "verses": None if self.verses is None else list(self.verses)}


def items_from_columns(order, moments, verses, catalog) -> list[PreparationItem]:
    """Convertit les anciennes sessions et les formats de sauvegarde existants."""
    if len(order) != len(moments) or len(order) != len(verses):
        raise ValueError("La préparation contient des chants, moments ou couplets incomplets.")
    return [PreparationItem(path, catalog.get(path, (path, None))[0], moment,
                            None if parts is None else list(parts))
            for path, moment, parts in zip(order, moments, verses)]


def move_item(items: list[PreparationItem], uid: str, offset: int) -> None:
    position = next((index for index, item in enumerate(items) if item.uid == uid), None)
    if position is None or not 0 <= position + offset < len(items):
        return
    items.insert(position + offset, items.pop(position))


def remove_item(items: list[PreparationItem], uid: str) -> None:
    position = next((index for index, item in enumerate(items) if item.uid == uid), None)
    if position is not None:
        items.pop(position)
