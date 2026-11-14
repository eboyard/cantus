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
from reportlab.platypus import BalancedColumns, BaseDocTemplate, Frame, PageTemplate, Paragraph

from scripts.song_selection import selected_song_parts, gospel_introduction, with_liturgical_introductions, reading_context, with_reading_introductions
from scripts.lyrics_format import formatted_lines, fragment_html
from scripts.song_types import IMPLICIT_MOMENTS, MOMENTS, celebration_moments, read_song_type


def _register_fonts() -> None:
    # Ces polices Unicode sont fournies par ReportLab, aussi sur Streamlit Cloud.
    fonts = Path(reportlab.__file__).parent / "fonts"
    if "CantusPrint" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("CantusPrint", str(fonts / "Vera.ttf")))
        pdfmetrics.registerFont(TTFont("CantusPrint-Bold", str(fonts / "VeraBd.ttf")))
        pdfmetrics.registerFontFamily("CantusPrint", normal="CantusPrint", bold="CantusPrint-Bold")


def _lyrics(text: str, *, bold: bool = False) -> str:
    return "<br/>".join(
        "".join(fragment_html(fragment, force_bold=bold) for fragment in line)
        for line in formatted_lines(text)
    )


class _Verse(Paragraph):
    """Ne coupe un couplet que s'il dépasse la hauteur d'une page."""

    def split(self, availWidth, availHeight):
        column_height = self.style.print_column_height
        if self.wrap(availWidth, column_height)[1] <= column_height:
            return []
        return super().split(availWidth, availHeight)


def create_print_song_sheet(
    title: str, songs: list[tuple[str, Path]], *, font_size: int = 11,
    moments: list[str] | None = None,
    verses: list[list[str] | None] | None = None,
    aelf_context: str | None = None,
) -> tuple[bytes, int]:
    """Retourne le PDF et son nombre de pages, sans réduire la taille du texte."""
    if not songs:
        raise ValueError("Ajoutez au moins un chant pour créer la feuille.")
    if font_size not in (9, 10, 11, 12):
        raise ValueError("Choisissez une taille de texte de 9, 10, 11 ou 12 points.")
    if moments is None:
        moments = celebration_moments([read_song_type(path) for _, path in songs])
    if len(moments) != len(songs) or any(moment not in ("", *MOMENTS) for moment in moments):
        raise ValueError("Choisissez une rubrique valide pour chaque chant.")
    if verses is not None and len(verses) != len(songs):
        raise ValueError("Choisissez les couplets pour chaque chant.")
    _register_fonts()
    body = ParagraphStyle("paroles", fontName="CantusPrint", fontSize=font_size,
                          leading=font_size + 1.6, spaceAfter=4, textColor="black")
    heading = ParagraphStyle("chant", parent=body, fontName="CantusPrint-Bold",
                             fontSize=font_size + .5, leading=font_size + 2,
                             spaceBefore=7, spaceAfter=3, keepWithNext=True)
    reading_heading = ParagraphStyle("lecture", parent=heading, keepWithNext=False)
    moment_style = ParagraphStyle("rubrique", parent=heading, fontSize=font_size + 1,
                                  leading=font_size + 3, spaceBefore=10)
    title_style = ParagraphStyle("celebration", parent=heading, fontSize=14, leading=17,
                                spaceBefore=0, spaceAfter=0)
    page_width, page_height = A4
    margin, gap = 12 * mm, 7 * mm
    title_paragraph = Paragraph(escape(title.strip() or "Messe"), title_style)
    _, title_height = title_paragraph.wrap(page_width - 2 * margin, page_height)
    height = page_height - 2 * margin - title_height - 5 * mm
    if height < 40 * mm:
        raise ValueError("Le titre de la célébration est trop long pour la feuille imprimable.")
    frames = [Frame(margin, margin, page_width - 2 * margin, height,
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
                    id="chants")]

    def decorate(canvas, document):
        canvas.saveState()
        title_paragraph.drawOn(canvas, margin, page_height - margin - title_height)
        canvas.setFont("CantusPrint", 8)
        canvas.drawRightString(page_width - margin, 6 * mm, f"Page {document.page}")
        canvas.restoreState()

    story = []
    context = reading_context(songs, aelf_context)
    gospel_intro = gospel_introduction([], context) if context else ""
    for position, (song_title, path) in enumerate(songs, start=1):
        parts = selected_song_parts(path, None if verses is None else verses[position - 1])
        parts = with_reading_introductions(parts, moments[position - 1], context)
        parts = with_liturgical_introductions(parts, moments[position - 1], gospel_intro)
        if not parts:
            raise ValueError(f"Le chant {path.name} ne contient aucune parole.")
        moment = moments[position - 1]
        song_heading = Paragraph(escape(song_title) if moment else f"{position}. {escape(song_title)}", heading)
        headings = []
        if moment and moment not in IMPLICIT_MOMENTS and (position == 1 or moment != moments[position - 2]):
            headings.append(Paragraph(escape(moment), moment_style))
        headings.extend(Paragraph(_lyrics(part.text), heading)
                        for part in parts if part.kind == "lecture" and part.identifier == "L1")
        headings.append(song_heading)
        heading_height = sum(
            paragraph.wrap(page_width - 2 * margin, height)[1]
            + paragraph.getSpaceBefore() + paragraph.getSpaceAfter()
            for paragraph in headings
        )
        song_body = ParagraphStyle("paroles-chant", parent=body,
                                   print_column_height=max(1, height - heading_height))
        paragraphs = []
        refrain_seen = False
        for part in parts:
            if part.kind == "lecture":
                continue
            if part.kind == "refrain":
                if refrain_seen:
                    text = "<b>Refrain</b>"
                else:
                    text = "<b>R.</b> " + _lyrics(part.text, bold=True)
                    refrain_seen = True
            elif part.selectable or part.kind == "pont":
                label = part.identifier[1:] + "." if part.selectable else "Pont."
                text = f"<b>{label}</b> " + _lyrics(part.text)
            else:
                text = _lyrics(part.text)
            paragraphs.append(_Verse(text, song_body))
        column_width = (page_width - 2 * margin - gap) / 2
        needed = min(song_body.print_column_height, max(
            paragraph.wrap(column_width, height)[1] for paragraph in paragraphs
        ))
        story.extend(headings)
        story.append(BalancedColumns(
            paragraphs, nCols=2, needed=needed,
            leftPadding=0, rightPadding=0, innerPadding=gap,
            topPadding=0, bottomPadding=0, endSlack=0,
        ))
        story.extend(Paragraph(_lyrics(part.text), reading_heading)
                     for part in parts if part.kind == "lecture" and part.identifier == "L2")
    output = BytesIO()
    document = BaseDocTemplate(output, pagesize=A4, title=title.strip() or "Messe",
                               author="CANTUS", pageCompression=1)
    document.addPageTemplates(PageTemplate(id="deux-colonnes", frames=frames, onPage=decorate))
    document.build(story)
    return output.getvalue(), document.page
