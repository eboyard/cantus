"""Types du carnet et moments liturgiques proposés pour une célébration."""

from pathlib import Path
import re
import unicodedata


MOMENTS = (
    "Chant d’entrée", "Préparation pénitentielle", "Gloire à Dieu", "Psaume",
    "Acclamation de l’Évangile", "Prières universelles", "Offertoire",
    "Sanctus", "Anamnèse", "Agneau de Dieu", "Communion", "Envoi",
)
TYPE_TAG = re.compile(
    r"^[ \t]*<!--[ \t]*type[ \t]*:([^\r\n]*?)-->[ \t]*\r?$",
    re.MULTILINE | re.IGNORECASE,
)


def _normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c)).replace("’", "'")


def song_type(markdown: str) -> str:
    """Privilégie le type déclaré ; ne déduit que les titres sans ambiguïté."""
    marker = TYPE_TAG.search(markdown)
    if marker:
        value = _normalize(marker.group(1).strip())
        aliases = {"gloria": MOMENTS[2], "kyrie": MOMENTS[1], "agnus dei": MOMENTS[9]}
        return next((moment for moment in MOMENTS if _normalize(moment) == value), aliases.get(value, ""))
    title_marker = re.search(r"<!--\s*titre\s*:\s*(.*?)-->", markdown, re.IGNORECASE)
    title = _normalize(title_marker.group(1).strip()) if title_marker else ""
    for pattern, moment in (
        (r"\bkyrie\b|^(seigneur,? )?prends pitie\b", MOMENTS[1]),
        (r"^gloria\b|^gloire a dieu\b|^grande paix, gloire a dieu\b", MOMENTS[2]),
        (r"^psaume\s+\d|\(psaume\s+\d", MOMENTS[3]),
        (r"^alleluia \(messe|^alleluia \(missa", MOMENTS[4]),
        (r"\bpriere[s]? universelle[s]?\b", MOMENTS[5]),
        (r"^sanctus\b|^saint,? le seigneur\b|^saint, saint, saint", MOMENTS[7]),
        (r"^anamnese\b", MOMENTS[8]),
        (r"^agnus\b|^agneau de dieu\b", MOMENTS[9]),
    ):
        if re.search(pattern, title):
            return moment
    return ""


def read_song_type(path: Path) -> str:
    return song_type(path.read_text(encoding="utf-8-sig"))


def set_song_type(markdown: str, moment: str) -> str:
    if moment not in ("", *MOMENTS):
        raise ValueError("Type de chant inconnu.")
    tag = f"<!-- type: {moment} -->"
    if TYPE_TAG.search(markdown):
        return TYPE_TAG.sub(lambda _: tag, markdown)
    return tag + "\n" + markdown
