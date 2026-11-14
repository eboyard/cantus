"""Sélection des couplets pour les exports, sans modifier le carnet de chants."""

from pathlib import Path
import json

from scripts.markdown_to_pptx import METADATA_TAG, SongPart, build_song_parts
from scripts.aelf import psalm_source_key


def reading_context(songs: list[tuple[str, Path]], aelf_context: str | None = None) -> str:
    if aelf_context is not None:
        if not psalm_source_key(aelf_context):
            raise ValueError("Les lectures AELF mémorisées sont invalides.")
        return aelf_context
    for _, path in songs:
        markdown = path.read_text(encoding="utf-8-sig")
        if psalm_source_key(markdown):
            return markdown
    return ""


def with_reading_introductions(parts: list[SongPart], moment: str, context: str) -> list[SongPart]:
    if parts and moment == "Psaume" and context:
        introductions = [part for part in build_song_parts(context) if part.kind == "lecture"]
        before = [part for part in introductions if part.identifier == "L1"]
        after = [part for part in introductions if part.identifier == "L2"]
        return before + [part for part in parts if part.kind != "lecture"] + after
    return parts


def gospel_introduction(songs: list[tuple[str, Path]], aelf_context: str | None = None) -> str:
    """Lit l'introduction de l'Évangile conservée avec le psaume AELF choisi."""
    markdown = reading_context(songs, aelf_context)
    if markdown:
        for marker in METADATA_TAG.finditer(markdown):
            if marker[1].lower() == "evangile_intro":
                try:
                    value = json.loads(marker[2])
                except ValueError:
                    raise ValueError("L’introduction de l’Évangile mémorisée est invalide.") from None
                if not isinstance(value, str):
                    raise ValueError("L’introduction de l’Évangile mémorisée doit être du texte.")
                return " ".join(value.split())
    return ""


def with_liturgical_introductions(parts: list[SongPart], moment: str, gospel_intro: str) -> list[SongPart]:
    introduction = ""
    if moment == "Anamnèse":
        introduction = "Notre Père"
    elif moment == "Acclamation de l’Évangile":
        introduction = gospel_intro
    if parts and introduction:
        text = f"**{introduction}**"
        if not any(part.kind == "lecture" and part.text == text for part in parts):
            return parts + [SongPart("L2", "lecture", text)]
    return parts


def selected_song_parts(path: Path, verses: list[str] | None = None) -> list[SongPart]:
    parts = build_song_parts(path.read_text(encoding="utf-8-sig"))
    if verses is None:
        return parts
    available = {part.identifier for part in parts if part.kind == "couplet"}
    if not set(verses).issubset(available):
        raise ValueError(f"Les couplets sélectionnés pour {path.name} n'existent plus. Vérifiez la sélection.")
    if not any(part.selectable for part in parts):
        return parts
    if not verses:
        result = []
        refrain_seen = False
        for part in parts:
            if part.selectable or (part.kind == "refrain" and refrain_seen):
                continue
            result.append(part)
            refrain_seen = refrain_seen or part.kind == "refrain"
        return result
    result = []
    omitted_verse = False
    for part in parts:
        if part.kind == "couplet":
            omitted_verse = part.selectable and part.identifier not in verses
            if omitted_verse:
                continue
        elif part.kind == "refrain":
            if omitted_verse:
                continue
        else:
            omitted_verse = False
        result.append(part)
    return result
