"""Sélection des couplets pour les exports, sans modifier le carnet de chants."""

from pathlib import Path

from scripts.markdown_to_pptx import SongPart, build_song_parts
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


def with_liturgical_introductions(
    parts: list[SongPart], moment: str, *, moments: list[str] | None = None,
) -> list[SongPart]:
    introduction = ""
    if moment == "Anamnèse" and (moments is None or "Notre Père" not in moments):
        introduction = "Notre Père"
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
