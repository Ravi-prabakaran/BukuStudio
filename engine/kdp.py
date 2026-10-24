"""Amazon KDP paperback print rules in one place. All lengths are in inches.

Sources: KDP Help, "Paperback Manuscript Formatting", "Paperback Cover" and
"Print Options". Re-check these numbers if KDP changes its specs.
"""
from dataclasses import dataclass

BLEED = 0.125            # added to top, bottom and outside edge of each interior page, and around the cover
DPI = 300                # minimum image resolution for print
SAFE = 0.375             # keep text and key art this far inside the trim on bleed books
SAFE_COVER = 0.125       # keep cover text this far inside the trim
SPINE_TEXT_MIN_PAGES = 80  # spine text only for books with more than 79 pages
SPINE_TEXT_MARGIN = 0.0625
BARCODE_W, BARCODE_H, BARCODE_INSET = 2.0, 1.2, 0.25  # kept clear on the back cover, lower right
KINDLE_COVER_PX = (1600, 2560)

# Paper thickness per page.
PAPER_THICKNESS = {
    ("bw", "white"): 0.002252,
    ("bw", "cream"): 0.0025,
    ("standard-color", "white"): 0.002252,
    ("premium-color", "white"): 0.002347,
}

MIN_PAGES = {"bw": 24, "standard-color": 72, "premium-color": 24}
MAX_PAGES = {"bw": 828, "standard-color": 600, "premium-color": 828}

# Inside (gutter) margin by page count, for the page side toward the spine.
GUTTER = [(150, 0.375), (300, 0.5), (500, 0.625), (700, 0.75), (828, 0.875)]


def trim_size(trim):
    w, h = (float(v) for v in trim.split("x"))
    return w, h


def gutter(pages):
    for limit, margin in GUTTER:
        if pages <= limit:
            return margin
    raise ValueError(f"{pages} pages is over KDP's maximum")


def spine_width(pages, interior, paper):
    try:
        return pages * PAPER_THICKNESS[(interior, paper)]
    except KeyError:
        raise ValueError(f"KDP has no {paper} paper for {interior} printing") from None


@dataclass
class Interior:
    trim_w: float
    trim_h: float
    bleed: bool
    pages: int

    @property
    def page_w(self):
        return self.trim_w + (BLEED if self.bleed else 0)

    @property
    def page_h(self):
        return self.trim_h + (2 * BLEED if self.bleed else 0)

    def trim_box(self, page_no):
        """(x, y, w, h) of the trimmed page within the PDF page. Odd pages are on
        the right (bleed on their right edge); even pages on the left."""
        b = BLEED if self.bleed else 0
        x = b if (self.bleed and page_no % 2 == 0) else 0
        return x, b, self.trim_w, self.trim_h

    def safe_box(self, page_no):
        """(x, y, w, h) where text must stay: outside margin SAFE (0.25 without
        bleed), gutter margin on the spine side."""
        x, y, w, h = self.trim_box(page_no)
        outside = SAFE if self.bleed else 0.25
        inside = max(gutter(self.pages), outside)
        left, right = (inside, outside) if page_no % 2 == 1 else (outside, inside)
        return x + left, y + SAFE if self.bleed else y + 0.25, w - left - right, h - 2 * (SAFE if self.bleed else 0.25)


@dataclass
class Cover:
    trim_w: float
    trim_h: float
    spine: float
    pages: int

    @property
    def width(self):
        return BLEED + self.trim_w + self.spine + self.trim_w + BLEED

    @property
    def height(self):
        return BLEED + self.trim_h + BLEED

    @property
    def back(self):
        return (BLEED, BLEED, self.trim_w, self.trim_h)

    @property
    def spine_box(self):
        return (BLEED + self.trim_w, BLEED, self.spine, self.trim_h)

    @property
    def front(self):
        return (BLEED + self.trim_w + self.spine, BLEED, self.trim_w, self.trim_h)

    @property
    def barcode(self):
        bx, by, bw, _ = self.back
        return (bx + bw - BARCODE_INSET - BARCODE_W, by + BARCODE_INSET, BARCODE_W, BARCODE_H)

    @property
    def spine_text_allowed(self):
        return self.pages >= SPINE_TEXT_MIN_PAGES

    def _inset(self, box, d):
        x, y, w, h = box
        return (x + d, y + d, w - 2 * d, h - 2 * d)

    @property
    def safe_front(self):
        return self._inset(self.front, SAFE_COVER)

    @property
    def safe_back(self):
        return self._inset(self.back, SAFE_COVER)


# Hardcover (case laminate). KDP's help gives the 15 mm wrap, 10 mm hinge, 0.635 in
# safe distance and barcode rules; the board allowances and spine allowance below
# come from cover calculators that reproduce KDP's cover-calculator output.
# Preflight tells users to confirm against kdp.amazon.com/cover-calculator.
HARDCOVER_TRIMS = {"5.5x8.5", "6x9", "6.14x9.21", "7x10", "8.25x11"}
HARDCOVER_PAGES = (75, 550)
HARDCOVER_INKS = {"bw", "premium-color"}
HC_WRAP = 0.591           # glued around the board edges (15 mm)
HC_BOARD_W = 0.197        # board width beyond the trim, front and back
HC_BOARD_H = 0.236        # board height beyond the trim, in total
HC_SPINE_EXTRA = 0.187    # spine allowance beyond the page block
HC_HINGE = 0.4            # keep text out of this space beside the spine (10 mm)
HC_SAFE = 0.635           # keep text this far from the edge of the book (16 mm)
HC_BARCODE_BOTTOM = 0.76  # barcode at least this far above the bottom of the book
HC_BARCODE_HINGE = 0.25   # and at least this far from the hinge


def hardcover_spine(pages, interior, paper):
    return spine_width(pages, interior, paper) + HC_SPINE_EXTRA


@dataclass
class HardcoverCover:
    trim_w: float
    trim_h: float
    spine: float
    pages: int

    @property
    def board_w(self):
        return self.trim_w + HC_BOARD_W

    @property
    def board_h(self):
        return self.trim_h + HC_BOARD_H

    @property
    def width(self):
        return 2 * HC_WRAP + 2 * self.board_w + self.spine

    @property
    def height(self):
        return 2 * HC_WRAP + self.board_h

    @property
    def back(self):
        return (HC_WRAP, HC_WRAP, self.board_w, self.board_h)

    @property
    def spine_box(self):
        return (HC_WRAP + self.board_w, HC_WRAP, self.spine, self.board_h)

    @property
    def front(self):
        return (HC_WRAP + self.board_w + self.spine, HC_WRAP, self.board_w, self.board_h)

    @property
    def safe_front(self):
        x, y, w, h = self.front
        return (x + HC_HINGE, y + HC_SAFE, w - HC_HINGE - HC_SAFE, h - 2 * HC_SAFE)

    @property
    def safe_back(self):
        x, y, w, h = self.back
        return (x + HC_SAFE, y + HC_SAFE, w - HC_SAFE - HC_HINGE, h - 2 * HC_SAFE)

    @property
    def barcode(self):
        x, y, w, _ = self.back
        return (x + w - HC_HINGE - HC_BARCODE_HINGE - BARCODE_W, y + HC_BARCODE_BOTTOM, BARCODE_W, BARCODE_H)

    @property
    def spine_text_allowed(self):
        return self.pages >= SPINE_TEXT_MIN_PAGES


def make_cover(settings, pages):
    """The cover geometry for this book's format."""
    tw, th = trim_size(settings["trim"])
    if settings["format"] == "hardcover":
        return HardcoverCover(tw, th, hardcover_spine(pages, settings["interior"], settings["paper"]), pages)
    return Cover(tw, th, spine_width(pages, settings["interior"], settings["paper"]), pages)


def check_print_options(settings, pages):
    """Return KDP rule errors for this format, print and page count."""
    errors = []
    interior, paper, fmt = settings["interior"], settings["paper"], settings["format"]
    if fmt == "hardcover":
        lo, hi = HARDCOVER_PAGES
        if not lo <= pages <= hi:
            errors.append(f"Hardcover needs {lo} to {hi} pages; this book has {pages}.")
        if settings["trim"] not in HARDCOVER_TRIMS:
            errors.append(f"Hardcover isn't made in {settings['trim']}. Sizes: {', '.join(sorted(HARDCOVER_TRIMS))}.")
        if interior not in HARDCOVER_INKS:
            errors.append(f"Hardcover can't use {interior} printing; choose black and white or premium color.")
    if (interior, paper) not in PAPER_THICKNESS:
        errors.append(f"KDP has no {paper} paper for {interior} printing.")
    if pages < MIN_PAGES[interior]:
        errors.append(f"{interior} printing needs at least {MIN_PAGES[interior]} pages; this book has {pages}.")
    if pages > MAX_PAGES[interior]:
        errors.append(f"{interior} printing allows at most {MAX_PAGES[interior]} pages; this book has {pages}.")
    if pages % 2:
        errors.append(f"Page count must be even; this book has {pages}.")
    return errors
