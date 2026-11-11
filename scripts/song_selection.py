"""Sélection des couplets pour les exports, sans modifier le carnet de chants."""

from pathlib import Path

from scripts.markdown_to_pptx import SongPart, build_song_parts


def selected_song_parts(path: Path, verses: list[str] | None = None) -> list[SongPart]:
    parts = build_song_parts(path.read_text(encoding="utf-8-sig"))
    if verses is None:
        return parts
    available = {part.identifier for part in parts if part.kind == "couplet"}
    if not set(verses).issubset(available):
        raise ValueError(f"Les couplets sélectionnés pour {path.name} n'existent plus. Vérifiez la sélection.")
    if not verses:
        result = []
        refrain_seen = False
        for part in parts:
            if part.kind == "couplet" or (part.kind == "refrain" and refrain_seen):
                continue
            result.append(part)
            refrain_seen = refrain_seen or part.kind == "refrain"
        return result
    result = []
    omitted_verse = False
    for part in parts:
        if part.kind == "couplet":
            omitted_verse = part.identifier not in verses
            if omitted_verse:
                continue
        elif part.kind == "refrain":
            if omitted_verse:
                continue
        else:
            omitted_verse = False
        result.append(part)
    return result
