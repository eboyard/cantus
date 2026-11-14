"""Import des célébrations et des psaumes depuis l'API publique AELF."""

from dataclasses import dataclass
from datetime import date
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import URLError
from urllib.request import Request, urlopen

from scripts.markdown_to_pptx import METADATA_TAG, build_slides, read_title


def mass_url(day: date) -> str:
    return f"https://www.aelf.org/{day.isoformat()}/romain/messe"


def api_url(day: date) -> str:
    return f"https://api.aelf.org/v1/messes/{day.isoformat()}/france"


@dataclass(frozen=True)
class AelfMass:
    day: date
    title: str
    name: str
    psalm_title: str
    reference: str
    markdown: str
    key: str

    @property
    def url(self) -> str:
        return mass_url(self.day)


class _TextParser(HTMLParser):
    """Ne conserve que le texte, les paragraphes et les sauts de ligne."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.ignored += 1
        elif not self.ignored and tag == "br":
            self.parts.append("\n")
        elif not self.ignored and tag in {"p", "div"}:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.ignored = max(0, self.ignored - 1)
        elif not self.ignored and tag in {"p", "div"}:
            self.parts.append("\n\n")

    def handle_data(self, text):
        if not self.ignored:
            self.parts.append(re.sub(r"\s+", " ", text))


def html_paragraphs(value: str) -> list[str]:
    if not isinstance(value, str):
        raise ValueError("Le texte du psaume reçu de l’AELF est invalide.")
    parser = _TextParser()
    parser.feed(value)
    text = "\n".join(line.strip() for line in "".join(parser.parts).splitlines())
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def parse_aelf_response(payload: dict, day: date) -> list[AelfMass]:
    if not isinstance(payload, dict) or not isinstance(payload.get("informations"), dict):
        raise ValueError("La réponse de l’API AELF est invalide.")
    info = payload["informations"]
    if info.get("date") != day.isoformat():
        raise ValueError("La date renvoyée par l’AELF ne correspond pas à la date demandée.")
    title = info.get("jour_liturgique_nom") or info.get("ligne1")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("Le nom de la célébration est absent de la réponse AELF.")
    title = " ".join(title.split())
    year = info.get("annee")
    if year in ("A", "B", "C"):
        title += f" — Année {year}"
    masses = payload.get("messes")
    if not isinstance(masses, list):
        raise ValueError("La liste des messes reçue de l’AELF est invalide.")
    result = []
    for mass in masses:
        if not isinstance(mass, dict) or not isinstance(mass.get("lectures"), list):
            raise ValueError("Les lectures reçues de l’AELF sont invalides.")
        for reading in mass["lectures"]:
            if not isinstance(reading, dict) or reading.get("type") != "psaume":
                continue
            reference = reading.get("ref")
            refrain = " ".join(html_paragraphs(reading.get("refrain_psalmique", "")))
            stanzas = html_paragraphs(reading.get("contenu", ""))
            if not isinstance(reference, str) or not reference.strip() or not refrain or not stanzas:
                raise ValueError("La référence, le refrain ou le texte du psaume AELF est incomplet.")
            reference = " ".join(reference.split())
            short = re.match(r"Ps\s+(\d+(?:\s*\(\d+\))?)", reference)
            name = f"Psaume {short[1]}" if short else f"Psaume ({reference})"
            psalm_title = f"{name} — {refrain}"
            index = len(result) + 1
            key = f"aelf/{day.isoformat()}/{index}"
            source = f"AELF : {api_url(day)}#psaume-{index}\nRéférence : {reference}"
            order = "R " + " ".join(f"C{i} R" for i in range(1, len(stanzas) + 1))
            blocks = [f"<!-- refrain -->\n{refrain}"]
            blocks.extend(f"<!-- couplet: C{i} -->\n{stanza}" for i, stanza in enumerate(stanzas, 1))
            markdown = (f"<!-- titre: {psalm_title} -->\n<!-- type: Psaume -->\n"
                        f"<!-- informations: {json.dumps(source, ensure_ascii=False)} -->\n"
                        f"<!-- ordre: {order} -->\n\n" + "\n\n---\n\n".join(blocks) + "\n")
            if not build_slides(markdown):
                raise ValueError("Le texte du psaume AELF est vide.")
            mass_name = mass.get("nom") or "Messe du jour"
            if not isinstance(mass_name, str):
                raise ValueError("Le nom de la messe reçu de l’AELF est invalide.")
            result.append(AelfMass(day, title, mass_name, psalm_title, reference, markdown, key))
    if not result:
        raise ValueError("Aucun psaume n’est proposé par l’AELF pour cette date.")
    return result


def load_aelf_masses(day: date) -> list[AelfMass]:
    request = Request(api_url(day), headers={"User-Agent": "Cantus/1.0", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            document = response.read(2_000_001)
        if len(document) > 2_000_000:
            raise ValueError("La réponse AELF reçue est trop volumineuse.")
        payload = json.loads(document.decode("utf-8-sig"))
    except (URLError, OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Impossible de récupérer la messe sur AELF. Vérifiez la connexion et réessayez.") from error
    return parse_aelf_response(payload, day)


def psalm_source_key(markdown: str) -> str | None:
    for marker in METADATA_TAG.finditer(markdown):
        if marker[1].lower() == "informations":
            try:
                value = json.loads(marker[2])
            except ValueError:
                continue
            if isinstance(value, str):
                match = re.match(r"\AAELF : https://api\.aelf\.org/v1/messes/(\d{4}-\d{2}-\d{2})/france#psaume-([1-9]\d*)(?:\n|$)", value)
                if match:
                    return f"aelf/{date.fromisoformat(match[1]).isoformat()}/{match[2]}"
    return None


def psalm_catalog(documents: dict[str, str], root: Path) -> dict[str, tuple[str, Path]]:
    """Recrée les psaumes de travail après réouverture d'une feuille publiée."""
    result = {}
    for key, markdown in documents.items():
        if (not isinstance(markdown, str) or len(markdown) > 100_000
                or psalm_source_key(markdown) != key or not build_slides(markdown)):
            raise ValueError("Le psaume AELF mémorisé est invalide.")
        directory = root / "temp" / "aelf"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"psaume-{sha256(markdown.encode()).hexdigest()}.md"
        if not path.exists():
            path.write_text(markdown, encoding="utf-8")
        result[key] = (read_title(path), path)
    return result
