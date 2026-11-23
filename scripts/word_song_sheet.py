"""Feuille Word modifiable, générée à partir du modèle paroissial DOTX."""

from copy import deepcopy
from datetime import date
from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile

from lxml import etree
from reportlab.pdfbase.pdfmetrics import stringWidth

from scripts.lyrics_format import formatted_lines
from scripts.song_selection import selected_song_parts, with_liturgical_introductions
from scripts.song_types import MOMENTS, celebration_moments, read_song_type


TEMPLATE = Path(__file__).resolve().parents[1] / "templates/feuille_chants.dotx"
DEFAULT_PLACE = "Église Saint Pierre – Boussy-Saint-Antoine"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{" + NS["w"] + "}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _element(tag, **attrs):
    element = etree.Element(W + tag)
    for key, value in attrs.items():
        element.set(W + key, str(value))
    return element


def _paragraph(text, style="CantusParoles", *, label="", force_bold=False, keep_next=False, lines=None):
    paragraph = _element("p")
    props = _element("pPr")
    props.append(_element("pStyle", val=style))
    if keep_next:
        props.append(_element("keepNext"))
    if style in {"CantusParoles", "CantusRefrain"} and len(text.splitlines()) <= 35:
        props.append(_element("keepLines"))
    paragraph.append(props)

    def add_run(content, bold=False, underline=False):
        run = _element("r")
        properties = _element("rPr")
        if bold:
            properties.append(_element("b"))
        if underline:
            properties.append(_element("u", val="single"))
        # Le soulignement et le gras des paroles sont indépendants du style du bloc.
        if len(properties):
            run.append(properties)
        value = _element("t")
        value.set(XML_SPACE, "preserve")
        value.text = content
        run.append(value)
        paragraph.append(run)

    if label:
        add_run(label, bold=True)
    for index, line in enumerate(formatted_lines(text) if lines is None else lines):
        if index:
            run = _element("r")
            run.append(_element("br"))
            paragraph.append(run)
        for fragment in line:
            add_run(fragment.text, fragment.bold or force_bold, fragment.underline)
    return paragraph


def _table(left, right, widths=(5300, 5300), *, keep_row=True):
    table = _element("tbl")
    props = _element("tblPr")
    props.append(_element("tblW", w=sum(widths), type="dxa"))
    props.append(_element("tblLayout", type="fixed"))
    borders = _element("tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        borders.append(_element(side, val="nil"))
    props.append(borders)
    margins = _element("tblCellMar")
    for side in ("top", "bottom", "left", "right"):
        margins.append(_element(side, w=0 if side in ("top", "bottom") else 50, type="dxa"))
    props.append(margins)
    table.append(props)
    grid = _element("tblGrid")
    for width in widths:
        grid.append(_element("gridCol", w=width))
    table.append(grid)
    row = _element("tr")
    if keep_row:
        row_props = _element("trPr")
        row_props.append(_element("cantSplit"))
        row.append(row_props)
    for width, content in zip(widths, (left, right)):
        cell = _element("tc")
        cell_props = _element("tcPr")
        cell_props.append(_element("tcW", w=width, type="dxa"))
        cell.append(cell_props)
        cell.extend(content)
        if not content or content[-1].tag != W + "p":
            cell.append(_paragraph(""))
        row.append(cell)
    table.append(row)
    return table


def _date_label(day):
    weekdays = ("Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche")
    months = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")
    return f"{weekdays[day.weekday()]} {day.day} {months[day.month - 1]} {day.year}"


def _slot(root, name):
    paragraphs = [p for p in root.xpath("//w:p", namespaces=NS)
                  if "".join(p.xpath("./w:r/w:t/text()", namespaces=NS)) == "{{" + name + "}}"]
    if len(paragraphs) != 1:
        raise ValueError(f"Le modèle Word doit contenir un seul emplacement {{{{{name}}}}}.")
    return paragraphs[0]


def _body_blocks(parts, font_size, *, two_columns=False):
    parts = [part for part in parts if part.kind != "lecture"]
    compact_triplet = (
        len(parts) == 3
        and all(part.kind == "couplet" for part in parts)
        and parts[0].identifier == parts[2].identifier
        and parts[0].identifier != parts[1].identifier
    )
    units = []
    refrain_seen = False
    for index, part in enumerate(parts):
        if compact_triplet and index == 2:
            continue
        if part.kind == "refrain":
            if refrain_seen:
                repeated = _paragraph("Refrain", force_bold=True)
                if units and units[-1][0] == "couplet":
                    units[-1][1].append(repeated)
                else:
                    units.append(("autre", [repeated], "Refrain"))
                continue
            refrain_seen = True
            units.append(("autre", [_paragraph(part.text, "CantusRefrain")], part.text))
        else:
            if compact_triplet:
                label = "1-3. " if index == 0 else "2. "
            else:
                label = part.identifier[1:] + ". " if part.selectable else "Pont. " if part.kind == "pont" else ""
            # Certains psaumes du carnet sont un seul bloc, sans séparateurs de strophes.
            if two_columns and part.kind == "couplet" and sum(p.kind == "couplet" for p in parts) == 1:
                lines = formatted_lines(part.text)
                if len(lines) > 1:
                    middle = (len(lines) + 1) // 2
                    breaks = [i for i in range(1, len(lines)) if not lines[i]]
                    if breaks:
                        middle = min(breaks, key=lambda i: abs(i - middle))
                    left = _paragraph(part.text, label=label, lines=lines[:middle])
                    right = _paragraph(part.text, lines=lines[middle + (not lines[middle]):])
                    units.append(("autre", [_table([left], [right], keep_row=False)], part.text))
                    continue
            units.append(("couplet" if part.kind == "couplet" else "autre",
                          [_paragraph(part.text, label=label)], part.text))

    def compact(unit):
        lines = formatted_lines(unit[2])
        widths = [sum(stringWidth(fragment.text, "Helvetica-Bold" if fragment.bold else "Helvetica", font_size)
                      for fragment in line) for line in lines]
        # Estimation prudente pour Calibri, avec une réserve pour la numérotation.
        return (unit[0] == "couplet" and len(lines) <= 20
                and (two_columns or max(widths, default=0) <= 275))

    blocks = []
    index = 0
    while index < len(units):
        if index + 1 < len(units) and compact(units[index]) and compact(units[index + 1]):
            blocks.append(_table(units[index][1], units[index + 1][1]))
            index += 2
        elif two_columns and compact(units[index]):
            # Une dernière strophe impaire conserve la largeur d’une colonne.
            blocks.append(_table(units[index][1], []))
            index += 1
        else:
            blocks.extend(units[index][1])
            index += 1
    return blocks


def create_word_song_sheet(
    title: str, songs: list[tuple[str, Path]], *, day: date | None = None,
    place: str = DEFAULT_PLACE, font_size: int = 12,
    moments: list[str] | None = None, verses: list[list[str] | None] | None = None,
    aelf_context: str | None = None, template_path: Path = TEMPLATE,
) -> bytes:
    """Produit un DOCX autonome ; Word calcule sa pagination à l’ouverture."""
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
    with ZipFile(template_path) as package:
        root = etree.fromstring(package.read("word/document.xml"))
        styles = etree.fromstring(package.read("word/styles.xml"))
        body = root.find("w:body", NS)
        year = re.search(r"\s*(?:[—–-]\s*)?Année\s+([ABC])\s*$", title, re.IGNORECASE)
        values = {"DATE": _date_label(day) if day else "", "LIEU": place.strip(),
                  "CELEBRATION": title[:year.start()].strip() if year else title.strip() or "Messe",
                  "ANNEE": f"Année {year[1].upper()}" if year else ""}
        for key, value in values.items():
            paragraph = _slot(root, key)
            if not value:
                paragraph.getparent().remove(paragraph)
            else:
                texts = paragraph.xpath("./w:r/w:t", namespaces=NS)
                texts[0].text = value
                for text in texts[1:]:
                    text.text = ""
        anchor = _slot(root, "CHANTS")
        if anchor.getparent() is not body:
            raise ValueError("L’emplacement {{CHANTS}} doit être dans le corps du modèle Word.")
        illustration = _slot(root, "ILLUSTRATION")
        illustration.getparent().remove(illustration)
        for text in illustration.xpath(".//w:t", namespaces=NS):
            text.text = ""
        insert_at = body.index(anchor)
        body.remove(anchor)
        blocks = []
        for position, (song_title, path) in enumerate(songs):
            parts = selected_song_parts(path, None if verses is None else verses[position])
            parts = with_liturgical_introductions(parts, moments[position], moments=moments)
            if not parts:
                raise ValueError(f"Le chant {path.name} ne contient aucune parole.")
            blocks.extend(_paragraph(part.text, "CantusLecture", keep_next=True) for part in parts
                          if part.kind == "lecture" and part.identifier == "L1")
            moment = moments[position]
            heading = _paragraph(moment + " :" if moment else song_title, "CantusRubrique")
            if moment:
                run = _element("r")
                props = _element("rPr")
                props.extend([_element("b", val=0), _element("u", val="none"), _element("i")])
                run.append(props)
                text = _element("t")
                text.set(XML_SPACE, "preserve")
                text.text = "  " + song_title
                run.append(text)
                heading.append(run)
            blocks.append(heading)
            content = _body_blocks(parts, font_size, two_columns=moment == "Psaume")
            if moment == "Agneau de Dieu":
                blocks.append(_table(content, [deepcopy(illustration)], widths=(8000, 2600), keep_row=False))
            else:
                blocks.extend(content)
            blocks.extend(_paragraph(part.text, "CantusLecture") for part in parts
                          if part.kind == "lecture" and part.identifier == "L2")
        for offset, block in enumerate(blocks):
            body.insert(insert_at + offset, block)
        for style in styles.xpath("//w:style[starts-with(@w:styleId, 'Cantus')]", namespaces=NS):
            size = style.find("w:rPr/w:sz", NS)
            if size is not None:
                size.set(W + "val", str(font_size * 2))
        output = BytesIO()
        with ZipFile(output, "w") as result:
            for member in package.infolist():
                data = package.read(member.filename)
                if member.filename == "word/document.xml":
                    data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
                elif member.filename == "word/styles.xml":
                    data = etree.tostring(styles, xml_declaration=True, encoding="UTF-8", standalone=True)
                elif member.filename == "[Content_Types].xml":
                    data = data.replace(b'wordprocessingml.template.main+xml', b'wordprocessingml.document.main+xml')
                elif member.filename == "docProps/core.xml":
                    core = etree.fromstring(data)
                    title_element = core.find("{http://purl.org/dc/elements/1.1/}title")
                    if title_element is not None:
                        title_element.text = title.strip() or "Messe"
                    data = etree.tostring(core, xml_declaration=True, encoding="UTF-8", standalone=True)
                result.writestr(member, data)
        return output.getvalue()
