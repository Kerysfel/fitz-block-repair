from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BoundingBox:
    top: float
    left: float
    bottom: float
    right: float

    @property
    def center(self) -> tuple[float, float]:
        return (self.left + self.right) / 2.0, (self.top + self.bottom) / 2.0

    def __or__(self, other: BoundingBox | None) -> BoundingBox:
        if other is None:
            return self

        return BoundingBox(
            top=min(self.top, other.top),
            left=min(self.left, other.left),
            bottom=max(self.bottom, other.bottom),
            right=max(self.right, other.right),
        )


@dataclass
class FontStyle:
    font: str
    size: float
    bold: bool
    italic: bool


@dataclass
class Span:
    text: str
    bbox: BoundingBox
    style: FontStyle


@dataclass
class Block:
    bbox: BoundingBox
    text: str
    style: FontStyle
    items: list[Span]


@dataclass(frozen=True)
class WatermarkCandidate:
    bbox: tuple[float, float, float, float]
    text: str
    signals: list[str]
    score: int


__all__ = [
    'BoundingBox',
    'FontStyle',
    'Span',
    'Block',
    'WatermarkCandidate',
]
