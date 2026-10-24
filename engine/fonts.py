"""Register BukuStudio's bundled fonts (SIL Open Font License, safe to embed in
commercial print books). ReportLab embeds a subset of each TTF in the PDF."""
from pathlib import Path

from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FILES = {
    "Andika": "Andika-Regular.ttf",
    "Andika-Bold": "Andika-Bold.ttf",
    "Gentium": "GentiumBookPlus-Regular.ttf",
    "Gentium-Bold": "GentiumBookPlus-Bold.ttf",
    "Gentium-Italic": "GentiumBookPlus-Italic.ttf",
    "Sniglet": "Sniglet-Regular.ttf",
    "Sniglet-ExtraBold": "Sniglet-ExtraBold.ttf",
}
_done = False


def register():
    global _done
    if _done:
        return
    for name, file in FILES.items():
        pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / file)))
    for family, regular, bold, italic in (("Andika", "Andika", "Andika-Bold", "Andika"),
                                          ("Gentium", "Gentium", "Gentium-Bold", "Gentium-Italic"),
                                          ("Sniglet", "Sniglet", "Sniglet-ExtraBold", "Sniglet")):
        addMapping(family, 0, 0, regular)
        addMapping(family, 1, 0, bold)
        addMapping(family, 0, 1, italic)
        addMapping(family, 1, 1, bold)
    # ReportLab otherwise declares Helvetica (never embedded) on every page,
    # which KDP rejects.
    from reportlab import rl_config
    rl_config.canvas_basefontname = "Andika"
    _done = True


def body_font(settings):
    """Andika (built for beginning readers) for picture books and early readers,
    Gentium for chapter books and novels."""
    return "Andika" if settings["bookType"] in ("picture", "early") else "Gentium"
