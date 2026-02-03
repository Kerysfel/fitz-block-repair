import argparse
from pathlib import Path

import fitz  # type: ignore

from textblock_clustering import TextClustering
from textblock_clustering.constants import (
    DISTANCE_THRESHOLD_DEFAULT,
    OVERLAP_THRESHOLD_DEFAULT,
    SHORT_SPAN_LIMIT_DEFAULT,
    BFS_VERTICAL_TOLERANCE,
)


def main() -> int:
    """
    Run a small CLI demo that clusters text spans on the first PDF page.

    Args:
        None.

    Returns:
        Process exit code, where 0 indicates success.
    """
    parser = argparse.ArgumentParser(description='Cluster text spans on the first page of a PDF.')
    parser.add_argument('pdf_path', help='Path to a PDF file')
    args = parser.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        raise SystemExit(f'PDF not found: {pdf_path}')

    with fitz.open(pdf_path) as doc:
        if doc.page_count == 0:
            raise SystemExit(f'Empty PDF: {pdf_path}')
        page = doc.load_page(0)  # type: ignore

        clustering = TextClustering(page)
        blocks = clustering.cluster_spans_bfs(
            distance_threshold=DISTANCE_THRESHOLD_DEFAULT,
            distance_vertical=BFS_VERTICAL_TOLERANCE,
            overlap_threshold=OVERLAP_THRESHOLD_DEFAULT,
            short_span_limit=SHORT_SPAN_LIMIT_DEFAULT,
        )

    print(f'blocks: {len(blocks)}')
    for i, block in enumerate(blocks[:5], start=1):
        print(f'{i}. {block.text}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
