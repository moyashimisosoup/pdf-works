"""Non-destructive in-memory page edits. No PDF is opened here."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class PageSpec:
    source_index: int
    rotation_delta: int = 0


class EditSession:
    def __init__(self, page_count: int):
        if page_count < 1:
            raise ValueError("PDF must have at least one page")
        self._pages = [PageSpec(i) for i in range(page_count)]
        self._history: list[list[PageSpec]] = []

    @property
    def pages(self) -> tuple[PageSpec, ...]:
        return tuple(self._pages)

    @property
    def can_undo(self) -> bool:
        return bool(self._history)

    def _record(self):
        self._history.append(self._pages.copy())
        if len(self._history) > 100:
            self._history.pop(0)

    def rotate(self, index: int, degrees: int):
        if degrees not in (-90, 90, 180):
            raise ValueError("Only right-angle rotation is supported in beta")
        item = self._pages[index]
        self._record()
        self._pages[index] = PageSpec(item.source_index, (item.rotation_delta + degrees) % 360)

    def delete(self, index: int):
        if len(self._pages) == 1:
            raise ValueError("The last remaining page cannot be removed")
        self._pages[index]
        self._record()
        del self._pages[index]

    def move(self, from_index: int, to_index: int):
        self._pages[from_index]
        if not 0 <= to_index < len(self._pages):
            raise IndexError("Destination page out of range")
        if from_index == to_index:
            return
        self._record()
        self._pages.insert(to_index, self._pages.pop(from_index))

    def undo(self) -> bool:
        if not self._history:
            return False
        self._pages = self._history.pop()
        return True

    def snapshot(self) -> list[tuple[int, int]]:
        return [(p.source_index, p.rotation_delta) for p in self._pages]
