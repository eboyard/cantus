"""Intitulés des lectures ajoutés comme éléments indépendants de la feuille."""

from hashlib import sha256
import json
from pathlib import Path

from scripts.markdown_to_pptx import METADATA_TAG, read_title


READINGS = (("lecture_avant", "Première lecture"), ("lecture_apres", "Deuxième lecture"),
            ("evangile_intro", "Évangile"))


def text_key(markdown: str) -> str:
    return "reading/" + sha256(markdown.encode("utf-8")).hexdigest()


def reading_documents(context: str) -> dict[str, str]:
    markers = {marker[1].lower(): marker[2] for marker in METADATA_TAG.finditer(context)}
    result = {}
    for marker, title in READINGS:
        if marker not in markers:
            continue
        value = json.loads(markers[marker])
        if not isinstance(value, str):
            raise ValueError("L’intitulé de la lecture doit être du texte.")
        value = " ".join(value.split())
        if value:
            markdown = f"<!-- titre: {title} -->\n<!-- type: {title} -->\n\n**{value}**\n"
            result[text_key(markdown)] = markdown
    return result


def reading_catalog(documents: dict[str, str], root: Path) -> dict[str, tuple[str, Path]]:
    result = {}
    for key, markdown in documents.items():
        if not isinstance(markdown, str) or len(markdown) > 100_000 or text_key(markdown) != key:
            raise ValueError("Le texte de lecture mémorisé est invalide.")
        directory = root / "temp" / "readings"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{key.split('/')[1]}.md"
        if not path.exists():
            path.write_text(markdown, encoding="utf-8")
        result[key] = (read_title(path), path)
    return result
