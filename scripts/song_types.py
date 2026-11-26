"""Types du carnet et moments liturgiques proposés pour une célébration."""

from pathlib import Path
import re
import unicodedata


MOMENTS = (
    "Chant d’entrée", "Préparation pénitentielle", "Gloire à Dieu", "Première lecture", "Psaume", "Cantique",
    "Deuxième lecture", "Acclamation de l’Évangile", "Évangile", "Prières universelles", "Offertoire",
    "Sanctus", "Anamnèse", "Notre Père", "Agneau de Dieu", "Communion", "Envoi",
)

IMPLICIT_MOMENTS = frozenset({
    "Gloire à Dieu", "Psaume", "Acclamation de l’Évangile", "Sanctus", "Anamnèse", "Notre Père", "Agneau de Dieu",
    "Première lecture", "Deuxième lecture", "Évangile",
})


def moment_insertion_index(moments: list[str], moment: str) -> int:
    """Insère un chant avant le premier moment liturgique qui le suit."""
    if moment not in MOMENTS:
        return len(moments)
    rank = MOMENTS.index(moment)
    return next((i for i, value in enumerate(moments)
                 if value in MOMENTS and MOMENTS.index(value) > rank), len(moments))


def celebration_moments(moments: list[str]) -> list[str]:
    """Propose les rubriques des extrémités uniquement si elles sont inconnues."""
    result = list(moments)
    if result:
        if not result[0]:
            result[0] = MOMENTS[0]
        if len(result) > 1 and not result[-1]:
            result[-1] = MOMENTS[-1]
    return result


TYPE_TAG = re.compile(
    r"^[ \t]*<!--[ \t]*type[ \t]*:([^\r\n]*?)-->[ \t]*\r?$",
    re.MULTILINE | re.IGNORECASE,
)


def _normalize(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.casefold())
                   if not unicodedata.combining(c)).replace("’", "'")


def song_type(markdown: str) -> str:
    """Privilégie le type déclaré ; ne déduit que les titres sans ambiguïté."""
    title_marker = re.search(r"<!--\s*titre\s*:\s*(.*?)-->", markdown, re.IGNORECASE)
    title = _normalize(title_marker.group(1).strip()) if title_marker else ""
    reading_types = {_normalize(moment): moment for moment in ("Première lecture", "Deuxième lecture", "Évangile")}
    marker = TYPE_TAG.search(markdown)
    if marker:
        value = _normalize(marker.group(1).strip())
        # Les anciens textes AELF avaient un type explicitement vide.
        if not value and title in reading_types:
            return reading_types[title]
        aliases = {"gloria": MOMENTS[2], "kyrie": MOMENTS[1], "agnus": "Agneau de Dieu", "agnus dei": "Agneau de Dieu"}
        return next((moment for moment in MOMENTS if _normalize(moment) == value), aliases.get(value, ""))
    if title in reading_types:
        return reading_types[title]
    # Le carnet nomme aussi les ordinaires « Messe de … - Gloria ».
    if re.match(r"^(messe|missa)\b", title):
        title = re.split(r"\s+[-–—]\s+", title)[-1]
    for pattern, moment in (
        (r"\bkyrie\b|^(seigneur,? )?prends pitie\b", MOMENTS[1]),
        (r"^gloria\b|^gloire a dieu\b|^grande paix, gloire a dieu\b", MOMENTS[2]),
        (r"^psaume\s+\d|\(psaume\s+\d", "Psaume"),
        (r"^alleluia$|^alleluia \(messe|^alleluia \(missa", "Acclamation de l’Évangile"),
        (r"\bpriere[s]? universelle[s]?\b", "Prières universelles"),
        (r"^sanctus\b|^saint,? le seigneur\b|^saint, saint, saint", "Sanctus"),
        (r"^anamnese\b", "Anamnèse"),
        (r"^notre pere\b|^pater noster\b", "Notre Père"),
        (r"^agnus\b|^agneau de dieu\b", "Agneau de Dieu"),
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
