"""Feuille PDF A4 en deux colonnes, avec refrains abrégés après leur première occurrence."""

from html import escape
from io import BytesIO
from pathlib import Path

import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph

from scripts.markdown_to_pptx import build_song_parts, styled_lines


def _register_fonts() -> None:
    # Ces polices Unicode sont fournies par ReportLab, aussi sur Streamlit Cloud.
    fonts = Path(reportlab.__file__).parent / "fonts"
    if "CantusPrint" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("CantusPrint", str(fonts / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("CantusPrint-Bold", str(fonts / "VeraBd.ttf")))
        pdfmetrics.registerFontFamily("CantusPrint", normal="CantusPrint", bold="CantusPrint-Bold")


def _lyrics(text: str, *, bold: bool = False) -> str:
    return "<br/>".join(
        "".join(f"<b>{escape(fragment)}</b>" if bold or emphasis else escape(fragment)
                for fragment, emphasis in line)
        for line in styled_lines(text)
    )


def create_print_song_sheet(
    title: str, songs: list[tuple[str, Path]], *, font_size: int = 11,
) -> tuple[bytes, int]:
    """Retourne le PDF et son nombre de pages, sans réduire la taille du texte."""
    if not songs:
        raise ValueError("Ajoutez au moins un chant pour créer la feuille.")
    if font_size not in (11, 12):
        raise ValueError("Choisissez une taille de texte de 11 ou 12 points.")
    _register_fonts()
    body = ParagraphStyle("paroles", fontName="CantusPrint", fontSize=font_size,
                          leading=font_size + 1.6, spaceAfter=4, textColor="black")
    heading = ParagraphStyle("chant", parent=body, fontName="CantusPrint-Bold",
                             fontSize=font_size + .5, leading=font_size + 2,
                             spaceBefore=7, spaceAfter=3, keepWithNext=True)
    title_style = ParagraphStyle("celebration", parent=heading, fontSize=14, leading=17,
                                spaceBefore=0, spaceAfter=0)
    page_width, page_height = A4
    margin, gap = 12 * mm, 7 * mm
    title_paragraph = Paragraph(escape(title.strip() or "Messe"), title_style)
    _, title_height = title_paragraph.wrap(page_width - 2 * margin, page_height)
    height = page_height - 2 * margin - title_height - 5 * mm
    if height < 40 * mm:
        raise ValueError("Le titre de la célébration est trop long pour la feuille imprimable.")
    column_width = (page_width - 2 * margin - gap) / 2
    frames = [Frame(margin + i * (column_width + gap), margin, column_width, height,
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                    id=f"colonne-{i}") for i in range(2)]

    def decorate(canvas, document):
        canvas.saveState()
        title_paragraph.drawOn(canvas, margin, page_height - margin - title_height)
        canvas.setFont("CantusPrint", 8)
        canvas.drawRightString(page_width - margin, 6 * mm, f"Page {document.page}")
        canvas.restoreState()

    story = []
    for position, (song_title, path) in enumerate(songs, start=1):
        parts = build_song_parts(path.read_text(encoding="utf-8-sig"))
        if not parts:
            raise ValueError(f"Le chant {path.name} ne contient aucune parole.")
        song_heading = Paragraph(f"{position}. {escape(song_title)}", heading)
        paragraphs = []
        refrain_seen = False
        for part in parts:
            if part.kind == "refrain":
                if refrain_seen:
                    text = "<b>Refrain</b>"
                else:
                    text = "<b>R.</b> " + _lyrics(part.text, bold=True)
                    refrain_seen = True
            else:
                label = part.identifier[1:] + "." if part.kind == "couplet" else "Pont."
                text = f"<b>{label}</b> " + _lyrics(part.text)
            # Un couplet reste ensemble s'il tient dans une colonne ; les blocs
            # exceptionnellement longs peuvent se poursuivre dans la suivante.
            paragraphs.append(Paragraph(text, body))
        story.append(KeepTogether([song_heading, paragraphs[0]]))
        story.extend(KeepTogether([paragraph]) for paragraph in paragraphs[1:])
    output = BytesIO()
    document = BaseDocTemplate(output, pagesize=A4, title=title.strip() or "Messe",
                               author="CANTUS", pageCompression=1)
    document.addPageTemplates(PageTemplate(id="deux-colonnes", frames=frames, onPage=decorate))
    document.build(story)
    return output.getvalue(), document.page
