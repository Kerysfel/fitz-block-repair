import fitz  # type: ignore

from .constants import (
    DOMAIN_RE,
    EMAIL_RE,
    TEXT_BLOCK_TYPE,
    PAD_DEFAULT,
    NEAR_WHITE_DEFAULT,
    SCORE_STRONG_WEIGHT,
    SIGNAL_URL_TEXT,
    SIGNAL_EMAIL_TEXT,
    SIGNAL_LINK_HIT,
    SIGNAL_NEAR_WHITE,
)
from .structures import Rect, RectSequence, RawBlockDict, RawLinkDict, RawSpanDict, RawTextDict
from .types import WatermarkCandidate


def _to_rect(bbox_seq: RectSequence | None) -> Rect:
    """
    Normalize a bounding-box sequence into a 4-tuple of floats.

    Args:
        bbox_seq: Sequence containing at least four numeric values, or None.

    Returns:
        A tuple of (x0, y0, x1, y1).

    Fallbacks:
        Returns (0.0, 0.0, 0.0, 0.0) when input is missing or too short.
    """
    if not bbox_seq or len(bbox_seq) < 4:
        return (0.0, 0.0, 0.0, 0.0)
    x0: float = float(bbox_seq[0])
    y0: float = float(bbox_seq[1])
    x1: float = float(bbox_seq[2])
    y1: float = float(bbox_seq[3])
    return (x0, y0, x1, y1)


def _intersects(a: Rect, b: Rect, pad: float = 0.0) -> bool:
    """
    Check whether two rectangles intersect, optionally expanding one by padding.

    Args:
        a: First rectangle as (x0, y0, x1, y1).
        b: Second rectangle as (x0, y0, x1, y1).
        pad: Padding applied to rectangle A in all directions.

    Returns:
        True if rectangles overlap with positive area, otherwise False.
    """
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    if pad:
        ax0 -= pad
        ay0 -= pad
        ax1 += pad
        ay1 += pad
    return (min(ax1, bx1) - max(ax0, bx0) > 0) and (min(ay1, by1) - max(ay0, by0) > 0)


def find_textual_watermarks_on_page(
    page: fitz.Page,
    use_color_hint: bool = True,
    external_links_only: bool = True,
    near_white_threshold: int = NEAR_WHITE_DEFAULT,
) -> list[WatermarkCandidate]:
    """
    Find candidate watermark spans by heuristics such as URLs, emails, links, and color.

    Args:
        page: PyMuPDF page to analyze.
        use_color_hint: Whether to treat near-white text as a weak signal.
        external_links_only: Whether to consider only links with a URI.
        near_white_threshold: Color value threshold for near-white detection.

    Returns:
        A list of watermark candidates sorted by score and position.

    Fallbacks:
        Returns an empty list when no candidates are detected.
    """
    data: RawTextDict = page.get_text('dict')  # type: ignore[attr-defined]
    blocks: list[RawBlockDict] = data.get('blocks', [])

    spans: list[RawSpanDict] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get('type') != TEXT_BLOCK_TYPE:
            continue
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                spans.append(span)

    link_rects: list[Rect] = []
    links: list[RawLinkDict] = page.get_links()  # type: ignore[attr-defined]
    for link in links:
        uri_present: bool = bool(link.get('uri'))
        if external_links_only and not uri_present:
            continue
        link_from = link.get('from')
        if link_from is not None:
            link_rect: Rect = (
                float(link_from.x0),
                float(link_from.y0),
                float(link_from.x1),
                float(link_from.y1),
            )
            link_rects.append(link_rect)

    candidates: list[WatermarkCandidate] = []
    for span in spans:
        text: str = str((span.get('text') or '')).strip()
        if not text:
            continue

        bbox: Rect = _to_rect(span.get('bbox'))
        color_int: int = int(span.get('color', 0))

        has_url: bool = DOMAIN_RE.search(text) is not None
        has_email: bool = EMAIL_RE.search(text) is not None
        link_hit: bool = any(_intersects(bbox, link_rect) for link_rect in link_rects)
        near_white: bool = use_color_hint and (color_int >= near_white_threshold)

        signals: list[str] = []
        if has_url:
            signals.append(SIGNAL_URL_TEXT)
        if has_email:
            signals.append(SIGNAL_EMAIL_TEXT)
        if link_hit:
            signals.append(SIGNAL_LINK_HIT)
        if near_white:
            signals.append(SIGNAL_NEAR_WHITE)

        if not signals:
            continue

        strong: int = int(has_url) + int(has_email) + int(link_hit)
        weak: int = int(near_white)

        if strong >= 1:
            score: int = strong * SCORE_STRONG_WEIGHT + weak
            candidate = WatermarkCandidate(bbox=bbox, text=text, signals=signals, score=score)
            candidates.append(candidate)

    candidates.sort(key=lambda c: (-c.score, c.bbox[1], c.bbox[0]))
    return candidates


def make_watermark_span_filter(
    page: fitz.Page,
    use_color_hint: bool = False,
    external_links_only: bool = True,
    pad: float = PAD_DEFAULT,
    near_white_threshold: int = NEAR_WHITE_DEFAULT,
):
    """
    Build a predicate that flags spans likely belonging to a watermark.

    Args:
        page: PyMuPDF page to analyze.
        use_color_hint: Whether to treat near-white text as a weak signal.
        external_links_only: Whether to consider only links with a URI.
        pad: Padding to apply when matching span boxes against candidates.
        near_white_threshold: Color value threshold for near-white detection.

    Returns:
        A function that accepts a span dict and returns True for watermark spans.

    Fallbacks:
        Returns a predicate that always yields False when no candidates are found.
    """
    candidates: list[WatermarkCandidate] = find_textual_watermarks_on_page(
        page=page,
        use_color_hint=use_color_hint,
        external_links_only=external_links_only,
        near_white_threshold=near_white_threshold,
    )
    wm_boxes: list[Rect] = [candidate.bbox for candidate in candidates]

    if not wm_boxes:
        return lambda span: False

    def _is_watermark_span(span: RawSpanDict) -> bool:
        """
        Test whether a span overlaps any candidate watermark box.

        Args:
            span: Span dictionary from PyMuPDF text extraction.

        Returns:
            True if the span overlaps any watermark candidate.
        """
        bbox: Rect = _to_rect(span.get('bbox'))
        return any(_intersects(bbox, wm_box, pad=pad) for wm_box in wm_boxes)

    return _is_watermark_span


__all__ = [
    'make_watermark_span_filter',
]
