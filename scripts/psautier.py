"""Reporte les repères de psalmodie sans remplacer les paroles de l'AELF."""

from functools import lru_cache
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.request import Request, urlopen


BASE_URL = "https://psautier.org/"
INDEX = json.loads(Path(__file__).with_name("psautier_index.json").read_text(encoding="utf-8"))
PSALM_REFERENCE = re.compile(
    r"(?:Ps(?:aume)?\.?\s+)?(\d+[ab]?)(?:\s*\((\d+)\))?(?=\s*(?:,|$))", re.IGNORECASE,
)


class _PsalmParser(HTMLParser):
    """Lit uniquement les cellules du texte, dans la première table après h1."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading = self.active = self.done = False
        self.column = 0
        self.in_cell = False
        self.bold = self.underline = self.ignored = 0
        self.chars = []
        self.breaks = set()

    def handle_starttag(self, tag, attrs):
        if tag == "h1":
            self.heading = True
        if tag == "table" and self.heading and not self.done:
            self.active = True
        if not self.active:
            return
        if tag == "tr":
            self.column = 0
        elif tag == "td":
            self.column += 1
            self.in_cell = self.column == 3
        elif self.in_cell:
            if tag in {"script", "style", "i", "sup"}:
                self.ignored += 1
            elif tag in {"b", "strong"}:
                self.bold += 1
            elif tag == "u":
                self.underline += 1
            elif tag == "br":
                self.breaks.add(len(self.chars))

    def handle_endtag(self, tag):
        if not self.active:
            return
        if tag == "table":
            self.active = False
            self.done = True
        elif tag == "td":
            if self.in_cell:
                self.breaks.add(len(self.chars))
            self.in_cell = False
        elif self.in_cell:
            if tag in {"script", "style", "i", "sup"}:
                self.ignored = max(0, self.ignored - 1)
            elif tag in {"b", "strong"}:
                self.bold = max(0, self.bold - 1)
            elif tag == "u":
                self.underline = max(0, self.underline - 1)

    def handle_data(self, text):
        if self.active and self.in_cell and not self.ignored:
            self.chars.extend((char, bool(self.bold), bool(self.underline)) for char in text)


def _normalized(chars):
    text, positions = [], []
    for position, char in enumerate(chars):
        for letter in unicodedata.normalize("NFKD", char.lower().replace("œ", "oe").replace("æ", "ae")):
            if letter.isalnum():
                text.append(letter)
                positions.append(position)
    return "".join(text), positions


def format_stanza(stanza: str, document: str) -> str:
    parser = _PsalmParser()
    parser.feed(document)
    source, source_positions = _normalized(char[0] for char in parser.chars)
    target, target_positions = _normalized(stanza)
    if not target:
        return stanza
    # Une correspondance ambiguë ne doit pas modifier la prière.
    matches = []
    for match in re.finditer(re.escape(target), source):
        left = source_positions[match.start()]
        right = source_positions[match.end() - 1] + 1
        if ((left and left not in parser.breaks and parser.chars[left - 1][0].isalnum())
                or (right < len(parser.chars) and right not in parser.breaks and parser.chars[right][0].isalnum())):
            continue
        matches.append(match)
    if len(matches) != 1:
        if not matches and "\n" in stanza:
            # La messe peut omettre des demi-versets entre deux lignes.
            # Chaque ligne est alors vérifiée séparément, sans ajouter les omissions.
            return "\n".join(format_stanza(line, document) for line in stanza.split("\n"))
        return stanza
    start = matches[0].start()
    styles = {}
    breaks = set()
    for index, target_position in enumerate(target_positions):
        source_position = source_positions[start + index]
        style = parser.chars[source_position][1:]
        previous = styles.get(target_position, style)
        if previous != style:
            return stanza  # Ligature dont les lettres auraient des styles différents.
        styles[target_position] = style
        if index:
            before = source_positions[start + index - 1]
            if any(before < boundary <= source_position for boundary in parser.breaks):
                # Place la coupure avant le mot, en conservant la ponctuation AELF.
                boundary = target_position
                while boundary and stanza[boundary - 1].isalnum():
                    boundary -= 1
                breaks.add(boundary)
    result = []
    opened = (False, False)
    for position, char in enumerate(stanza):
        style = styles.get(position, (False, False))
        if style != opened or position in breaks:
            if opened[1]:
                result.append("</u>")
            if opened[0]:
                result.append("**")
            if position in breaks and result and not "".join(result).rstrip(" \t\r").endswith("\n"):
                result.append("\n")
            if style[0]:
                result.append("**")
            if style[1]:
                result.append("<u>")
            opened = style
        result.append(escape(char, quote=False))
    if opened[1]:
        result.append("</u>")
    if opened[0]:
        result.append("**")
    return re.sub(r"[^\S\n]*\n[^\S\n]*", "\n", "".join(result))


@lru_cache(maxsize=192)
def _download(page: str) -> str:
    request = Request(BASE_URL + page, headers={"User-Agent": "Cantus/1.0", "Accept": "text/html"})
    with urlopen(request, timeout=8) as response:
        data = response.read(1_000_001)
    if len(data) > 1_000_000:
        raise ValueError("Page psautier.org trop volumineuse.")
    return data.decode("utf-8-sig")


def format_stanzas(reference: str, stanzas: list[str]) -> tuple[list[str], str | None]:
    match = PSALM_REFERENCE.match(reference)
    if not match:
        return stanzas, None
    number = match[1].lower()
    pages = [INDEX[number]] if number in INDEX else [INDEX[key] for key in (number + "a", number + "b") if key in INDEX]
    if not pages:
        return stanzas, None
    try:
        documents = [(page, _download(page)) for page in pages]
        formatted = list(stanzas)
        used = []
        for page, document in documents:
            updated = [format_stanza(stanza, document) if stanza == original else stanza
                       for stanza, original in zip(formatted, stanzas)]
            if updated != formatted:
                used.append(BASE_URL + page)
            formatted = updated
    except (OSError, ValueError):
        return stanzas, None
    return formatted, ", ".join(used) or None
