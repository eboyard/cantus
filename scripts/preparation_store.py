"""Brouillons privés, indépendants des exports et de la publication GitHub."""

from datetime import date
import json
import os
from pathlib import Path
import re
import tempfile

from scripts.song_types import MOMENTS


MAX_BYTES = 5_000_000
FIELDS = (
    "celebration_title", "celebration_date", "song_order", "song_moments", "song_verses",
    "aelf_psalms", "reading_texts", "selected_aelf_context", "selected_daily_psalm",
    "pages_parish", "word_place",
)


def encode_preparation(state) -> bytes:
    data = {key: state[key] for key in FIELDS if key in state}
    if isinstance(data.get("celebration_date"), date):
        data["celebration_date"] = data["celebration_date"].isoformat()
    # Valider les tableaux internes avant de les regrouper, sans tronquer une
    # sélection incohérente avec zip.
    decode_preparation(json.dumps({"version": 1, "preparation": data}, ensure_ascii=False).encode("utf-8"))
    order = data.pop("song_order", [])
    moments = data.pop("song_moments", [])
    verses = data.pop("song_verses", [])
    data["songs"] = [
        {"path": key, "moment": moment, "verses": parts}
        for key, moment, parts in zip(order, moments, verses)
    ]
    raw = (json.dumps({"version": 2, "preparation": data}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    decode_preparation(raw)
    return raw


def decode_preparation(raw: bytes) -> dict:
    """Valide intégralement avant de remplacer une préparation en cours."""
    if len(raw) > MAX_BYTES:
        raise ValueError("Le fichier de préparation est trop volumineux.")
    try:
        document = json.loads(raw)
        if not isinstance(document, dict) or type(document.get("version")) is not int or document["version"] not in (1, 2):
            raise ValueError
        data = document["preparation"]
        fields = set(FIELDS)
        if document["version"] == 2:
            fields = fields - {"song_order", "song_moments", "song_verses"} | {"songs"}
        if not isinstance(data, dict) or set(data) - fields:
            raise ValueError
        if document["version"] == 2:
            songs = data.pop("songs", [])
            if not isinstance(songs, list) or len(songs) > 500:
                raise ValueError
            if any(not isinstance(song, dict) or set(song) != {"path", "moment", "verses"} for song in songs):
                raise ValueError
            data["song_order"] = [song["path"] for song in songs]
            data["song_moments"] = [song["moment"] for song in songs]
            data["song_verses"] = [song["verses"] for song in songs]
        order = data.get("song_order", [])
        moments = data.get("song_moments", [])
        verses = data.get("song_verses", [])
        if not isinstance(order, list) or len(order) > 500:
            raise ValueError
        # Les clés sont résolues dans le catalogue, jamais comme chemins libres.
        if not all(isinstance(key, str) and 0 < len(key) <= 500 for key in order):
            raise ValueError
        if not isinstance(moments, list) or len(moments) != len(order) or any(m not in ("", *MOMENTS) for m in moments):
            raise ValueError
        if not isinstance(verses, list) or len(verses) != len(order):
            raise ValueError
        if any(v is not None and (not isinstance(v, list) or not all(
                isinstance(part, str) and re.fullmatch(r"[A-Z][0-9]*", part) for part in v)) for v in verses):
            raise ValueError
        for field in ("aelf_psalms", "reading_texts"):
            docs = data.get(field, {})
            if not isinstance(docs, dict) or not all(isinstance(k, str) and isinstance(v, str)
                                                     and len(v) <= 100_000 for k, v in docs.items()):
                raise ValueError
        for field in ("celebration_title", "pages_parish", "word_place"):
            if field in data and not isinstance(data[field], str):
                raise ValueError
        if "pages_parish" in data and data["pages_parish"] not in ("Boussy-saint-Antoine", "Quincy-sous-Sénart"):
            raise ValueError
        for field in ("selected_aelf_context", "selected_daily_psalm"):
            if field in data and data[field] is not None and not isinstance(data[field], str):
                raise ValueError
        if "celebration_date" in data:
            data["celebration_date"] = date.fromisoformat(data["celebration_date"])
        return data
    except (ValueError, KeyError, TypeError, UnicodeError, RecursionError):
        raise ValueError("Le fichier de préparation est invalide ou incompatible.") from None


def draft_path(directory: Path, identifier: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{64}", identifier):
        raise ValueError("Lien de reprise invalide.")
    return directory / f"{identifier}.json"


def save_preparation(directory: Path, identifier: str, raw: bytes) -> None:
    """Un échec d'écriture laisse intact le dernier brouillon complet."""
    target = draft_path(directory, identifier)
    decode_preparation(raw)
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_preparation(directory: Path, identifier: str) -> dict:
    with draft_path(directory, identifier).open("rb") as stream:
        return decode_preparation(stream.read(MAX_BYTES + 1))
