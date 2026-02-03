"""
Shared structure aliases for raw PyMuPDF dictionaries and geometry.
"""

import fitz  # type: ignore

Point = tuple[float, float]
Rect = tuple[float, float, float, float]
RectSequence = list[float] | tuple[float, ...]

RawSpanDict = dict[str, str | int | float | RectSequence | None]
RawLineDict = dict[str, list[RawSpanDict]]
RawBlockDict = dict[str, int | list[RawLineDict]]
RawTextDict = dict[str, list[RawBlockDict]]

LinkFrom = fitz.Rect
RawLinkDict = dict[str, str | LinkFrom | None]

DrawingRect = fitz.Rect
DrawingLineItem = tuple[str, Point, Point]
DrawingRectItem = tuple[str, DrawingRect]
DrawingItem = DrawingLineItem | DrawingRectItem
RawDrawingDict = dict[str, DrawingRect | list[DrawingItem]]

__all__ = [
    'Point',
    'Rect',
    'RectSequence',
    'RawSpanDict',
    'RawLineDict',
    'RawBlockDict',
    'RawTextDict',
    'LinkFrom',
    'RawLinkDict',
    'DrawingRect',
    'DrawingLineItem',
    'DrawingRectItem',
    'DrawingItem',
    'RawDrawingDict',
]
