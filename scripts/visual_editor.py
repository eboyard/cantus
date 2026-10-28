"""Éditeur de paroles sans exposition de la syntaxe Markdown."""

from dataclasses import dataclass
from pathlib import Path
import re

import streamlit as st
import streamlit.components.v1 as components

from scripts.lyrics_format import editor_html_to_markdown, lyrics_html


_component = components.declare_component("cantus_lyrics_editor", path=str(Path(__file__).with_name("visual_editor")))
_separator = re.compile(r"(?m)^[ \t]*---[ \t]*\r?$\n?")
_prefix = re.compile(r"\A(?:\s*<!--[\s\S]*?-->\s*)*")


@dataclass(frozen=True)
class Section:
    prefix: str
    text: str
    suffix: str
    separator: str
    label: str


def split_sections(document: str) -> list[Section]:
    parts = _separator.split(document)
    separators = [match[0] for match in _separator.finditer(document)] + [""]
    result = []
    counts = {"couplet": 0, "pont": 0}
    for part, separator in zip(parts, separators):
        prefix = _prefix.match(part)[0]
        content = part[len(prefix):]
        text = content.rstrip()
        suffix = content[len(text):]
        marker = re.search(r"<!--\s*(refrain|couplet|pont)(?:\s*:\s*([CP]\d+))?\s*-->", prefix, re.IGNORECASE)
        kind = marker[1].lower() if marker else "couplet"
        if kind == "refrain":
            label = "Refrain"
        else:
            counts[kind] += 1
            number = marker[2][1:] if marker and marker[2] else str(counts[kind])
            label = ("Couplet " if kind == "couplet" else "Pont ") + number
        result.append(Section(prefix, text, suffix, separator, label))
    return result


def merge_sections(document: str, changes: dict) -> str:
    sections = split_sections(document)
    if not isinstance(changes, dict) or any(not isinstance(key, str) or not key.isdigit()
                                           or int(key) >= len(sections) or not isinstance(value, str)
                                           for key, value in changes.items()):
        raise ValueError("Le contenu de l’éditeur est invalide. Rechargez le chant avant de réessayer.")
    return "".join(section.prefix + (editor_html_to_markdown(changes[str(index)])
                                    if str(index) in changes else section.text)
                   + section.suffix + section.separator
                   for index, section in enumerate(sections))


def visual_song_editor(document: str, *, key: str, disabled: bool = False) -> tuple[str, str]:
    sections = split_sections(document)
    value = _component(
        sections=[{"id": str(index), "label": section.label, "html": lyrics_html(section.text)}
                  for index, section in enumerate(sections)],
        disabled=disabled, key=key, default=None,
    )
    if not isinstance(value, dict):
        return document, ""
    lyrics = merge_sections(document, value.get("changes", {}))
    event_id = value.get("event_id")
    if event_id == st.session_state.get(key + "_event"):
        return lyrics, ""
    st.session_state[key + "_event"] = event_id
    return lyrics, value.get("action", "")
