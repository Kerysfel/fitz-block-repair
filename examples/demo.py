from dataclasses import dataclass
from pathlib import Path

import fitz  # type: ignore

from textblock_clustering import TextClustering
from textblock_clustering.constants import (
    DISTANCE_THRESHOLD_DEFAULT,
    OVERLAP_THRESHOLD_DEFAULT,
    SHORT_SPAN_LIMIT_DEFAULT,
    BFS_VERTICAL_TOLERANCE,
)
from textblock_clustering.structures import Rect, RectSequence, RawLineDict

EXAMPLES_DIR = Path(__file__).resolve().parent
DATA_DIR = EXAMPLES_DIR / 'data'
ARTIFACTS_DIR = EXAMPLES_DIR / 'artifacts'

# Select which PDF to process by filename from examples/data.
SELECTED_PDF = 'SR_Example.pdf'

PAGE_NUMBER = 0

COLOR_PALETTE = [
    (230, 57, 70),
    (29, 53, 87),
    (69, 123, 157),
    (241, 250, 238),
    (168, 218, 220),
    (255, 140, 0),
    (0, 128, 0),
    (138, 43, 226),
]


@dataclass
class ExtractedBlock:
    bbox: Rect
    text: str


@dataclass
class MethodResult:
    name: str
    blocks: list[ExtractedBlock]
    image_name: str


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


def _rgb(color: tuple[int, int, int]) -> tuple[float, float, float]:
    """
    Convert an RGB tuple (0-255) to PyMuPDF color floats (0-1).

    Args:
        color: RGB tuple in 0-255 range.

    Returns:
        A tuple of floats between 0 and 1.
    """
    return (color[0] / 255.0, color[1] / 255.0, color[2] / 255.0)


def extract_blocks_from_blocks(page: fitz.Page) -> list[ExtractedBlock]:
    """
    Extract block bounding boxes using PyMuPDF's "blocks" mode.

    Args:
        page: PyMuPDF page to analyze.

    Returns:
        List of extracted blocks with bounding boxes and text.
    """
    blocks: list[ExtractedBlock] = []
    for item in page.get_text('blocks'):
        x0, y0, x1, y1, text, _block_no, block_type = item
        if block_type != 0:
            continue
        text_value = str(text).strip()
        if not text_value:
            continue
        blocks.append(ExtractedBlock(bbox=(float(x0), float(y0), float(x1), float(y1)), text=text_value))
    return blocks


def _join_lines(lines: list[RawLineDict]) -> str:
    """
    Join line/span structures into a readable block of text.

    Args:
        lines: List of line dictionaries with spans.

    Returns:
        Text joined by line breaks.
    """
    line_texts: list[str] = []
    for line in lines:
        spans = line.get('spans', [])
        parts: list[str] = []
        for span in spans:
            parts.append(str(span.get('text', '')))
        joined = ''.join(parts).strip()
        if joined:
            line_texts.append(joined)
    return '\n'.join(line_texts).strip()


def extract_blocks_from_dict(page: fitz.Page, mode: str) -> list[ExtractedBlock]:
    """
    Extract block bounding boxes using PyMuPDF's dict-like modes.

    Args:
        page: PyMuPDF page to analyze.
        mode: One of "dict" or "rawdict".

    Returns:
        List of extracted blocks with bounding boxes and text.
    """
    data = page.get_text(mode)
    blocks: list[ExtractedBlock] = []
    for block in data.get('blocks', []):
        if block.get('type') != 0:
            continue
        text_value = _join_lines(block.get('lines', []))
        if not text_value:
            continue
        bbox = _to_rect(block.get('bbox'))
        blocks.append(ExtractedBlock(bbox=bbox, text=text_value))
    return blocks


def extract_blocks_from_words(page: fitz.Page) -> list[ExtractedBlock]:
    """
    Build block-like groups from PyMuPDF's "words" mode.

    Args:
        page: PyMuPDF page to analyze.

    Returns:
        List of extracted blocks with bounding boxes and text.
    """
    words = page.get_text('words')
    by_block = {}
    order: list[int] = []

    for item in words:
        x0, y0, x1, y1, word, block_no, line_no, word_no = item
        if block_no not in by_block:
            by_block[block_no] = {
                'bbox': [float(x0), float(y0), float(x1), float(y1)],
                'words': [],
            }
            order.append(block_no)

        entry = by_block[block_no]
        bbox = entry['bbox']
        bbox[0] = min(bbox[0], float(x0))
        bbox[1] = min(bbox[1], float(y0))
        bbox[2] = max(bbox[2], float(x1))
        bbox[3] = max(bbox[3], float(y1))
        entry['words'].append((int(line_no), int(word_no), str(word)))

    blocks: list[ExtractedBlock] = []
    for block_no in order:
        entry = by_block[block_no]
        words = entry['words']
        line_map = {}
        for line_no, word_no, word in words:
            line_map.setdefault(line_no, []).append((word_no, word))

        lines: list[str] = []
        for line_no in sorted(line_map.keys()):
            words_sorted = [w for _, w in sorted(line_map[line_no])]
            line_text = ' '.join(words_sorted).strip()
            if line_text:
                lines.append(line_text)

        text_value = '\n'.join(lines).strip()
        if not text_value:
            continue
        x0, y0, x1, y1 = entry['bbox']
        blocks.append(ExtractedBlock(bbox=(x0, y0, x1, y1), text=text_value))

    return blocks


def extract_blocks_from_clustering(page: fitz.Page) -> list[ExtractedBlock]:
    """
    Extract block bounding boxes using the custom clustering algorithm.

    Args:
        page: PyMuPDF page to analyze.

    Returns:
        List of extracted blocks with bounding boxes and text.
    """
    clustering = TextClustering(page)
    blocks = clustering.cluster_spans_bfs(
        distance_threshold=DISTANCE_THRESHOLD_DEFAULT,
        distance_vertical=BFS_VERTICAL_TOLERANCE,
        overlap_threshold=OVERLAP_THRESHOLD_DEFAULT,
        short_span_limit=SHORT_SPAN_LIMIT_DEFAULT,
    )
    results: list[ExtractedBlock] = []
    for block in blocks:
        bbox = (block.bbox.left, block.bbox.top, block.bbox.right, block.bbox.bottom)
        results.append(ExtractedBlock(bbox=bbox, text=block.text))
    return results


def render_rects_to_png(pdf_path: Path, page_number: int, rects: list[Rect], out_path: Path) -> None:
    """
    Render a page with colored rectangles and save to PNG.

    Args:
        pdf_path: Path to the PDF file.
        page_number: Zero-based page index to render.
        rects: Rectangles to draw.
        out_path: Output PNG path.

    Returns:
        None.
    """
    with fitz.open(pdf_path) as src:
        tmp = fitz.open()
        tmp.insert_pdf(src, from_page=page_number, to_page=page_number)
        page = tmp.load_page(0)

        for idx, rect in enumerate(rects):
            color = _rgb(COLOR_PALETTE[idx % len(COLOR_PALETTE)])
            page.draw_rect(fitz.Rect(rect), color=color, width=1)

        pix = page.get_pixmap()
        pix.save(out_path)
        tmp.close()


def format_blocks_for_md(blocks: list[ExtractedBlock]) -> str:
    """
    Format blocks into a readable Markdown snippet.

    Args:
        blocks: Extracted blocks to format.

    Returns:
        A formatted string with block separators.
    """
    parts: list[str] = []
    for idx, block in enumerate(blocks, start=1):
        text = block.text.strip()
        if not text:
            continue
        parts.append(f'[{idx}]\n{text}')
    return '\n\n---\n\n'.join(parts).strip()


def write_report_md(
    report_path: Path,
    source_pdf: Path,
    page_number: int,
    method_results: list[MethodResult],
    clustered: MethodResult,
) -> None:
    """
    Write a Markdown report comparing extraction methods.

    Args:
        report_path: Output Markdown path.
        source_pdf: PDF being processed.
        page_number: Zero-based page index.
        method_results: Results from PyMuPDF extraction methods.
        clustered: Result from custom clustering.

    Returns:
        None.
    """
    lines: list[str] = []
    lines.append('# Text Extraction Demo')
    lines.append(f'Source: {source_pdf.name}')
    lines.append(f'Page: {page_number + 1} (0-based {page_number})')

    for result in method_results:
        lines.append('')
        lines.append(f'## PyMuPDF: {result.name}')
        lines.append(f'Image: {result.image_name}')
        lines.append('')
        lines.append('```')
        lines.append(format_blocks_for_md(result.blocks))
        lines.append('```')

    lines.append('')
    lines.append('## Custom Clustering')
    lines.append(f'Image: {clustered.image_name}')
    lines.append('')
    lines.append('```')
    lines.append(format_blocks_for_md(clustered.blocks))
    lines.append('```')

    report_path.write_text('\n'.join(lines), encoding='utf-8')


def main() -> int:
    """
    Generate demo artifacts for the selected PDF.

    Args:
        None.

    Returns:
        Process exit code, where 0 indicates success.
    """
    pdf_path = DATA_DIR / SELECTED_PDF
    if not pdf_path.exists():
        raise SystemExit(f'PDF not found: {pdf_path}')

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            raise SystemExit(f'Empty PDF: {pdf_path}')
        page = doc.load_page(PAGE_NUMBER)

        results: list[MethodResult] = []

        blocks_blocks = extract_blocks_from_blocks(page)
        results.append(MethodResult(name='blocks', blocks=blocks_blocks, image_name='01_blocks.png'))

        blocks_dict = extract_blocks_from_dict(page, 'dict')
        results.append(MethodResult(name='dict', blocks=blocks_dict, image_name='02_dict.png'))

        blocks_rawdict = extract_blocks_from_dict(page, 'rawdict')
        results.append(MethodResult(name='rawdict', blocks=blocks_rawdict, image_name='03_rawdict.png'))

        blocks_words = extract_blocks_from_words(page)
        results.append(MethodResult(name='words', blocks=blocks_words, image_name='04_words.png'))

        clustered_blocks = extract_blocks_from_clustering(page)
        clustered_result = MethodResult(
            name='clustered',
            blocks=clustered_blocks,
            image_name='05_clustered.png',
        )

    for result in results:
        rects = [block.bbox for block in result.blocks]
        render_rects_to_png(pdf_path, PAGE_NUMBER, rects, ARTIFACTS_DIR / result.image_name)

    render_rects_to_png(pdf_path, PAGE_NUMBER, [b.bbox for b in clustered_result.blocks], ARTIFACTS_DIR / clustered_result.image_name)

    report_path = ARTIFACTS_DIR / 'report.md'
    write_report_md(report_path, pdf_path, PAGE_NUMBER, results, clustered_result)

    print(f'Artifacts written to: {ARTIFACTS_DIR}')
    print(f'Report: {report_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
