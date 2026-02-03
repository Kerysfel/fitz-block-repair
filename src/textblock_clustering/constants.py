import re

# Distance (in points) for grouping nearby spans into the same block.
DISTANCE_THRESHOLD_DEFAULT: float = 65.0
# Horizontal gap/overlap tolerance (in points) for line-based adjacency.
OVERLAP_THRESHOLD_DEFAULT: float = 3.0
# Minimum span length to avoid merging with neighbors.
SHORT_SPAN_LIMIT_DEFAULT: int = 4
# Vertical tolerance (in points) for considering spans on the same line.
BFS_VERTICAL_TOLERANCE: float = 5.0
# Multiplier for span height to cap vertical gaps within a single text block.
LINE_GAP_HEIGHT_MULTIPLIER: float = 1.35

# Drawing-based underline detection thresholds.
DRAWING_Y_TOLERANCE_PX: float = 4.0
# Minimum underline length to treat a drawing as a signature line.
DRAWING_MIN_LENGTH_PX: float = 30.0
# Minimum underscore segments to treat text as a real underline.
UNDERLINE_MIN_SEGMENTS: int = 4
# Max Y distance to align a signature line with a title block.
SIGN_SAME_LINE_Y_TOL_PX: int = 16
# Minimum horizontal gap after the title to look for a signature line.
SIGN_LINE_RIGHT_MIN_GAP_PX: int = 5
# Rough scale to convert line length into underscore count.
UNDERLINE_PIXELS_PER_CHAR: int = 7
# Fallback minimum underscore length when synthesizing a line.
UNDERLINE_MIN_CHARS: int = 5
# Vertical padding when creating a fake underline span.
FAKE_UNDERLINE_Y_PAD_PX: int = 1
# Font used for synthesized underline spans (visual debugging/readability).
FAKE_UNDERLINE_FONT_NAME: str = 'Times New Roman'
# Size for synthesized underline spans (points).
FAKE_UNDERLINE_FONT_SIZE_PT: float = 14.0

# Heuristics for detecting textual watermarks.
DOMAIN_RE: re.Pattern = re.compile(
    r"\b(?:https?://)?(?:[a-z0-9-]+\.)+[a-z]{2,}\b",
    re.IGNORECASE,
)
# Email pattern used as a watermark signal.
EMAIL_RE: re.Pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# PyMuPDF block type for text.
TEXT_BLOCK_TYPE: int = 0
# Signals used to explain why a span looks like a watermark.
SIGNAL_URL_TEXT: str = 'URL_TEXT'
SIGNAL_EMAIL_TEXT: str = 'EMAIL_TEXT'
SIGNAL_LINK_HIT: str = 'LINK_HIT'
SIGNAL_NEAR_WHITE: str = 'NEAR_WHITE'

# Light text threshold treated as "near white" in RGB integer form.
NEAR_WHITE_DEFAULT: int = 0xF0_F0_F0
# Padding added around watermark boxes when filtering spans.
PAD_DEFAULT: float = 0.5
# Weight for strong watermark signals vs. weak ones.
SCORE_STRONG_WEIGHT: int = 3

__all__ = [
    'DISTANCE_THRESHOLD_DEFAULT',
    'OVERLAP_THRESHOLD_DEFAULT',
    'SHORT_SPAN_LIMIT_DEFAULT',
    'BFS_VERTICAL_TOLERANCE',
    'LINE_GAP_HEIGHT_MULTIPLIER',
    'DRAWING_Y_TOLERANCE_PX',
    'DRAWING_MIN_LENGTH_PX',
    'UNDERLINE_MIN_SEGMENTS',
    'SIGN_SAME_LINE_Y_TOL_PX',
    'SIGN_LINE_RIGHT_MIN_GAP_PX',
    'UNDERLINE_PIXELS_PER_CHAR',
    'UNDERLINE_MIN_CHARS',
    'FAKE_UNDERLINE_Y_PAD_PX',
    'FAKE_UNDERLINE_FONT_NAME',
    'FAKE_UNDERLINE_FONT_SIZE_PT',
    'DOMAIN_RE',
    'EMAIL_RE',
    'TEXT_BLOCK_TYPE',
    'SIGNAL_URL_TEXT',
    'SIGNAL_EMAIL_TEXT',
    'SIGNAL_LINK_HIT',
    'SIGNAL_NEAR_WHITE',
    'NEAR_WHITE_DEFAULT',
    'PAD_DEFAULT',
    'SCORE_STRONG_WEIGHT',
]
