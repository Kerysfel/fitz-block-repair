from __future__ import annotations

import copy
import math
import re
from pathlib import Path

import fitz  # type: ignore

from .constants import (
    DISTANCE_THRESHOLD_DEFAULT,
    DRAWING_MIN_LENGTH_PX,
    DRAWING_Y_TOLERANCE_PX,
    FAKE_UNDERLINE_FONT_NAME,
    FAKE_UNDERLINE_FONT_SIZE_PT,
    FAKE_UNDERLINE_Y_PAD_PX,
    OVERLAP_THRESHOLD_DEFAULT,
    SHORT_SPAN_LIMIT_DEFAULT,
    BFS_VERTICAL_TOLERANCE,
    SIGN_LINE_RIGHT_MIN_GAP_PX,
    SIGN_SAME_LINE_Y_TOL_PX,
    UNDERLINE_MIN_CHARS,
    UNDERLINE_MIN_SEGMENTS,
    UNDERLINE_PIXELS_PER_CHAR,
)
from .exceptions import EmptyPDFError
from .types import BoundingBox, Span, Block, FontStyle
from .watermark import make_watermark_span_filter


class TextClustering:
    def __init__(self, page: fitz.Page) -> None:
        self.page: fitz.Page = page
        self.spans: list[Span] = self.extract_spans()
        self.drawings: list[dict] = page.get_drawings()  # type: ignore

    @staticmethod
    def euclid_dist(p1: tuple[float, float], p2: tuple[float, float]) -> float:
        return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

    def maybe_join_text(self, prev_text: str, next_text: str) -> str:
        if not prev_text:
            return next_text

        next_text = next_text.lstrip()
        if not next_text:
            return prev_text

        last_char = prev_text[-1]
        first_char = next_text[0]

        if last_char.isalpha() and first_char.isalpha():
            if first_char.isupper():
                return prev_text + ' ' + next_text

            rus_vowels = (
                '\u0430\u0435\u0451\u0438\u043e\u0443\u044b\u044d\u044e\u044f'
                '\u0410\u0415\u0401\u0418\u041e\u0423\u042b\u042d\u042e\u042f'
            )
            if last_char in rus_vowels:
                return prev_text + ' ' + next_text

            return prev_text + next_text

        if last_char in (' ', '-', '\u2014', '\u2013'):
            return prev_text + next_text

        return prev_text + ' ' + next_text

    def inject_missing_underscores(
        self,
        text_blocks: list[Block],
        drawings: list[dict],
        y_tolerance: float = DRAWING_Y_TOLERANCE_PX,
        min_length: float = DRAWING_MIN_LENGTH_PX,
    ) -> list[Block]:
        u: re.Pattern = re.compile(rf'_{(UNDERLINE_MIN_SEGMENTS,)}|_(?:\s*_){(3,)}')

        def collect_horizontal_lines(draws: list[dict]) -> list[tuple[float, float, float, float]]:
            lines: list[tuple[float, float, float, float]] = []
            for d in draws:
                r = d.get('rect')
                if r is not None:
                    if abs(r.y0 - r.y1) <= y_tolerance and (r.x1 - r.x0) >= min_length:
                        lines.append((r.x0, r.y0, r.x1, r.y1))
                for it in d.get('items', []):
                    op = it[0]
                    if op == 'l':  # ('l', (x0,y0), (x1,y1))
                        (x0, y0), (x1, y1) = it[1], it[2]
                        if abs(y0 - y1) <= y_tolerance and abs(x1 - x0) >= min_length:
                            x_left, x_right = sorted([x0, x1])
                            lines.append((x_left, y0, x_right, y1))
                    elif op == 're':  # ('re', rect)
                        rr = it[1]
                        if abs(rr.y0 - rr.y1) <= y_tolerance and (rr.x1 - rr.x0) >= min_length:
                            lines.append((rr.x0, rr.y0, rr.x1, rr.y1))
            return lines

        def mid_y(bbox: BoundingBox) -> float:
            return (bbox.top + bbox.bottom) / 2.0

        lines: list[tuple[float, float, float, float]] = collect_horizontal_lines(drawings)
        if not lines:
            return text_blocks

        pos_re: re.Pattern = re.compile(
            r'(\u0440\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c'
            r'|\u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0440'
            r'|\u043f\u0440\u043e\u0440\u0435\u043a\u0442\u043e\u0440'
            r'|\u0437\u0430\u0432\u0435\u0434\u0443\u044e\u0449\u0438\u0439'
            r'|\u043d\u0430\u0447\u0430\u043b\u044c\u043d\u0438\u043a)',
            re.IGNORECASE,
        )
        new_blocks: list[Block] = list(text_blocks)

        for left_block in text_blocks:
            if not pos_re.search(left_block.text):
                continue

            y_leader: float = mid_y(left_block.bbox)
            already: bool = any(
                abs(mid_y(b2.bbox) - y_leader) <= SIGN_SAME_LINE_Y_TOL_PX and u.search(b2.text) for b2 in text_blocks
            )
            if already:
                continue

            candidate: tuple[float, float, float, float] | None = None
            y_tol = SIGN_SAME_LINE_Y_TOL_PX
            for x0, y0, x1, y1 in lines:
                overlaps_vertically: bool = not (
                    (y1 < left_block.bbox.top - y_tol) or (y0 > left_block.bbox.bottom + y_tol)
                )
                if overlaps_vertically and (x1 > left_block.bbox.right + SIGN_LINE_RIGHT_MIN_GAP_PX):
                    candidate = (x0, y0, x1, y1)
                    break

            if candidate:
                x0, y0, x1, y1 = candidate
                underline_len: int = max(UNDERLINE_MIN_CHARS, int((x1 - x0) // UNDERLINE_PIXELS_PER_CHAR))
                fake_span: Span = Span(
                    text='_' * underline_len,
                    bbox=BoundingBox(
                        top=y0 - FAKE_UNDERLINE_Y_PAD_PX,
                        left=x0,
                        bottom=y1 + FAKE_UNDERLINE_Y_PAD_PX,
                        right=x1,
                    ),
                    style=FontStyle(
                        font=FAKE_UNDERLINE_FONT_NAME,
                        size=FAKE_UNDERLINE_FONT_SIZE_PT,
                        bold=False,
                        italic=False,
                    ),
                )
                new_blocks.append(
                    Block(bbox=fake_span.bbox, text=fake_span.text, style=fake_span.style, items=[fake_span])
                )

        return new_blocks

    def extract_spans(self, page: fitz.Page | None = None) -> list[Span]:
        target_page: fitz.Page = page if page is not None else self.page
        skip_wm = make_watermark_span_filter(target_page, use_color_hint=False, external_links_only=True)

        data = target_page.get_text('dict')
        result: list[Span] = []

        for block in data.get('blocks', []):  # type: ignore
            if block.get('type') != 0:
                continue

            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    if skip_wm(span):
                        continue

                    txt = span.get('text', '')
                    if not txt.strip():
                        continue

                    bbox_vals = span.get('bbox', [0, 0, 0, 0])
                    bbox = BoundingBox(
                        top=bbox_vals[1],
                        left=bbox_vals[0],
                        bottom=bbox_vals[3],
                        right=bbox_vals[2],
                    )
                    style = FontStyle(
                        font=span.get('font', ''),
                        size=float(span.get('size', 0.0)),
                        bold=('Bold' in span.get('font', '')),
                        italic=('Italic' in span.get('font', '')),
                    )
                    result.append(Span(text=txt.strip(), bbox=bbox, style=style))

        return result

    def merge_short_spans(self, items: list[Span], short_span_limit: int) -> list[Span]:
        if not items:
            return []

        def only_underscores(text: str) -> bool:
            return re.fullmatch(r'_+', text) is not None

        def only_dashes(text: str) -> bool:
            return re.fullmatch(r'[\u2013\u2014-]+', text) is not None

        merged: list[Span] = [copy.copy(items[0])]
        for i in range(1, len(items)):
            current = items[i]
            prev = merged[-1]

            if len(current.text) < short_span_limit:
                if (only_underscores(prev.text) and only_underscores(current.text)) or (
                    only_dashes(prev.text) and only_dashes(current.text)
                ):
                    sep = ''
                else:
                    sep = ' '
                prev.text = prev.text + sep + current.text
                prev.bbox = prev.bbox | current.bbox
            else:
                merged.append(copy.copy(current))

        return merged

    def cluster_spans_bfs(
        self,
        distance_threshold: float,
        distance_vertical: float,
        overlap_threshold: float,
        short_span_limit: int,
    ) -> list[Block]:
        spans: list[Span] = self.spans
        n = len(spans)
        if not spans:
            raise EmptyPDFError('Empty PDF page: no text spans found.')

        adjacency: list[list[int]] = [[] for _ in range(n)]
        centers: list[tuple[float, float]] = [span.bbox.center for span in spans]

        for i in range(n):
            bbox_i = spans[i].bbox
            (x0i, y0i, x1i, y1i) = (bbox_i.left, bbox_i.top, bbox_i.right, bbox_i.bottom)
            center_i = centers[i]

            for j in range(i + 1, n):
                bbox_j = spans[j].bbox
                (x0j, y0j, x1j, y1j) = (bbox_j.left, bbox_j.top, bbox_j.right, bbox_j.bottom)
                center_j = centers[j]

                is_same_block = self.euclid_dist(center_i, center_j) < distance_threshold

                if not is_same_block:
                    yi_mid = (y0i + y1i) / 2.0
                    yj_mid = (y0j + y1j) / 2.0

                    is_same_block = abs(yi_mid - yj_mid) < distance_vertical and (
                        abs(x1i - x0j) < overlap_threshold or abs(x1j - x0i) < overlap_threshold
                    )

                if is_same_block:
                    adjacency[i].append(j)
                    adjacency[j].append(i)

        clusters: list[list[int]] = []
        visited = [False] * n

        for idx in range(n):
            if visited[idx]:
                continue

            queue = [idx]
            visited[idx] = True
            comp = [idx]
            while queue:
                cur = queue.pop(0)
                for neighbor in adjacency[cur]:
                    if not visited[neighbor]:
                        visited[neighbor] = True
                        queue.append(neighbor)
                        comp.append(neighbor)

            clusters.append(comp)

        blocks: list[Block] = []
        for comp in clusters:
            items: list[Span] = sorted([spans[k] for k in comp], key=lambda s: (s.bbox.top, s.bbox.left))
            items = self.merge_short_spans(items, short_span_limit=short_span_limit)

            left = min(s.bbox.left for s in items)
            top = min(s.bbox.top for s in items)
            right = max(s.bbox.right for s in items)
            bottom = max(s.bbox.bottom for s in items)

            text_merged = ''
            for span in items:
                text_merged = self.maybe_join_text(text_merged, span.text)

            first_span = items[0]
            min_size = min(sp.style.size for sp in items)
            is_bold = any(sp.style.bold for sp in items)
            block_style = FontStyle(
                font=first_span.style.font,
                size=min_size,
                bold=is_bold,
                italic=first_span.style.italic,
            )

            blocks.append(
                Block(
                    bbox=BoundingBox(top=top, left=left, bottom=bottom, right=right),
                    text=text_merged,
                    style=block_style,
                    items=items,
                )
            )

        blocks = self.inject_missing_underscores(blocks, self.drawings)
        blocks.sort(key=lambda b: (b.bbox.top, b.bbox.left))
        return blocks

    @classmethod
    def cluster_pdf_spans(
        cls,
        pdf_path: Path | str,
        page_number: int = 0,
        distance_threshold: float = DISTANCE_THRESHOLD_DEFAULT,
        distance_vertical: float = BFS_VERTICAL_TOLERANCE,
        overlap_threshold: float = OVERLAP_THRESHOLD_DEFAULT,
        short_span_limit: int = SHORT_SPAN_LIMIT_DEFAULT,
    ) -> list[Block]:
        with fitz.open(pdf_path) as doc:
            if not doc.page_count:
                raise FileNotFoundError(f'Empty or missing PDF: {pdf_path}')

            page = doc.load_page(page_number)  # type: ignore
            instance = cls(page)

        return instance.cluster_spans_bfs(
            distance_threshold=distance_threshold,
            distance_vertical=distance_vertical,
            overlap_threshold=overlap_threshold,
            short_span_limit=short_span_limit,
        )


__all__ = [
    'TextClustering',
]
