"""Sélection des couplets et versets, sans modifier le carnet de chants."""

from dataclasses import replace
from pathlib import Path
import re

from scripts.markdown_to_pptx import SongPart, build_song_parts
from scripts.aelf import psalm_source_key
from scripts.song_types import song_type


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
    markdown = path.read_text(encoding="utf-8-sig")
    parts = build_song_parts(markdown)
    psalm = song_type(markdown) in {"Psaume", "Cantique"}
    legacy_psalm = psalm and not any(part.explicit for part in parts)
    if legacy_psalm and not re.search(r"<!--[ \t]*ordre[ \t]*:", markdown, re.IGNORECASE):
        # Les anciens psaumes utilisent --- ou de simples lignes vides pour
        # séparer les strophes. Les numéros restent stables après sélection.
        stanzas = [stanza.strip() for part in parts
                   for stanza in re.split(r"\n[ \t]*\n", part.text) if stanza.strip()]
        parts = [SongPart(f"C{index}", "couplet", text, explicit=True)
                 for index, text in enumerate(stanzas, 1)]
    elif psalm:
        parts = [replace(part, explicit=True) if part.kind == "couplet" else part for part in parts]
    # Avant la sélection des psaumes, [] signifiait « aucun couplet balisé »
    # et conservait tout le texte. Les anciens brouillons restent lisibles.
    if verses is None or (legacy_psalm and verses == []):
        return parts
    available = {part.identifier for part in parts if part.kind == "couplet"}
    if not set(verses).issubset(available):
        label = "versets" if psalm else "couplets"
        raise ValueError(f"Les {label} sélectionnés pour {path.name} n'existent plus. Vérifiez la sélection.")
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
