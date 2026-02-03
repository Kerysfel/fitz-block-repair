from dataclasses import dataclass

from .structures import Point, Rect


@dataclass
class BoundingBox:
    top: float
    left: float
    bottom: float
    right: float

    @property
    def center(self) -> Point:
        """
        Compute the geometric center of the bounding box.

        Args:
            None.

        Returns:
            A (x, y) tuple representing the center point.
        """
        return (self.left + self.right) / 2.0, (self.top + self.bottom) / 2.0

    def __or__(self, other: "BoundingBox | None") -> "BoundingBox":
        """
        Merge two bounding boxes into one that fully contains both.

        Args:
            other: Another bounding box or None.

        Returns:
            A new bounding box covering both inputs.

        Fallbacks:
            Returns self when other is None.
        """
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
    bbox: Rect
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
