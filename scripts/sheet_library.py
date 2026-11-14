"""Retrouve les feuilles existantes et rapproche leurs chants du carnet."""

import base64
import json
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
from urllib.error import HTTPError

from scripts.github_publish import GitHubPublishError, _nested_sha, _request
from scripts.song_selection import selected_song_parts


@dataclass(frozen=True)
class ExistingSheet:
    path: str
    sha: str = ""

    @property
    def label(self) -> str:
        parish, day, _ = self.path.split("/")
        names = {"boussy-saint-antoine": "Boussy-saint-Antoine", "quincy-sous-senart": "Quincy-sous-Sénart"}
        return f"{names.get(parish, parish)} — {date.fromisoformat(day).strftime('%d/%m/%Y')}"


def _is_sheet(path: str) -> bool:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*/\d{4}-\d{2}-\d{2}/index\.html", path):
        return False
    try:
        date.fromisoformat(path.split("/")[1])
        return True
    except ValueError:
        return False


def _sort(sheets: list[ExistingSheet]) -> list[ExistingSheet]:
    return sorted(sheets, key=lambda sheet: (sheet.path.split("/")[1], sheet.path), reverse=True)


def local_sheets(root: Path) -> list[ExistingSheet]:
    return _sort([ExistingSheet(path.relative_to(root).as_posix())
                  for path in root.glob("*/????-??-??/index.html")
                  if _is_sheet(path.relative_to(root).as_posix()) and path.resolve().is_relative_to(root.resolve())])


def published_sheets(token: str, repository: str, branch: str) -> list[ExistingSheet]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not branch.strip():
        raise ValueError("La configuration du dépôt ou de la branche GitHub est invalide.")
    endpoint = f"https://api.github.com/repos/{repository}/git"
    try:
        reference = _request("GET", f"{endpoint}/ref/heads/{quote(branch, safe='/')}", token)
        commit = _request("GET", f"{endpoint}/commits/{_nested_sha(reference, 'object')}", token)
        tree = _request("GET", f"{endpoint}/trees/{_nested_sha(commit, 'tree')}?recursive=1", token)
        if tree.get("truncated") is not False or not isinstance(tree.get("tree"), list):
            raise ValueError("GitHub n'a pas fourni la liste complète des feuilles. Réessayez plus tard.")
        sheets = []
        for entry in tree["tree"]:
            if not isinstance(entry, dict):
                raise ValueError("La liste des feuilles reçue de GitHub est invalide.")
            path = entry.get("path", "")
            if isinstance(path, str) and path.startswith("docs/") and _is_sheet(path[5:]) and entry.get("type") == "blob" and entry.get("mode") in ("100644", "100755"):
                sha = entry.get("sha", "")
                if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40,64}", sha):
                    raise ValueError("La référence d'une feuille reçue de GitHub est invalide.")
                sheets.append(ExistingSheet(path[5:], sha))
        return _sort(sheets)
    except HTTPError:
        raise GitHubPublishError("Impossible de lire les feuilles sur GitHub. Vérifiez le dépôt, la branche et les droits du jeton.") from None


def read_existing_sheet(sheet: ExistingSheet, root: Path, token: str, repository: str) -> str:
    if not _is_sheet(sheet.path):
        raise ValueError("Le chemin de la feuille est invalide.")
    if not sheet.sha:
        path = (root / sheet.path).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("La feuille doit se trouver dans le dossier docs.")
        return path.read_text(encoding="utf-8-sig")
    if not re.fullmatch(r"[a-f0-9]{40,64}", sheet.sha) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("La référence de la feuille GitHub est invalide.")
    try:
        blob = _request("GET", f"https://api.github.com/repos/{repository}/git/blobs/{sheet.sha}", token)
        if blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
            raise ValueError("Le contenu de la feuille reçu de GitHub est invalide.")
        return base64.b64decode("".join(blob["content"].split()), validate=True).decode("utf-8-sig")
    except HTTPError:
        raise GitHubPublishError("Impossible de télécharger cette feuille depuis GitHub. Actualisez la liste et réessayez.") from None


class _ContentsParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_contents = False
        self.anchor: tuple[str, list[str]] | None = None
        self.songs: list[tuple[str, str]] = []
        self.section_key: str | None = None
        self.heading: list[str] | None = None
        self.section_songs: list[tuple[str, str]] = []
        self.section_verses: list[str | None] = []
        self.current_verses: str | None = None

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "section" and re.fullmatch(r"chant-\d+", attrs.get("id") or ""):
            self.section_key = attrs.get("data-song-key") or ""
            self.current_verses = attrs.get("data-song-verses")
        if tag == "h2" and self.section_key is not None:
            self.heading = []
        if tag == "nav" and attrs.get("id") == "sommaire":
            self.in_contents = True
        if self.in_contents and tag == "a" and (attrs.get("href") or "").startswith("#chant-"):
            self.anchor = (attrs.get("data-song-key") or "", [])

    def handle_data(self, text):
        if self.anchor is not None:
            self.anchor[1].append(text)
        if self.heading is not None:
            self.heading.append(text)

    def handle_endtag(self, tag):
        if tag == "h2" and self.heading is not None:
            title = " ".join("".join(self.heading).split())
            self.section_songs.append((self.section_key or "", re.sub(r"^\d+\.\s+", "", title)))
            self.section_verses.append(self.current_verses)
            self.heading = None
        if tag == "section":
            self.section_key = None
        if tag == "a" and self.anchor is not None:
            key, text = self.anchor
            self.songs.append((key, " ".join("".join(text).split())))
            self.anchor = None
        if tag == "nav":
            self.in_contents = False


def _normalized_title(title: str) -> str:
    title = unicodedata.normalize("NFKD", title.casefold())
    return "".join(char for char in title if char.isalnum() and not unicodedata.combining(char))


def songs_from_contents(document: str, catalog: dict[str, tuple[str, Path]]) -> list[str]:
    parser = _ContentsParser()
    parser.feed(document)
    songs = parser.songs or parser.section_songs
    if not songs:
        raise ValueError("Cette feuille ne contient pas de liste de chants reconnue.")
    result = []
    issues = []
    for source_key, title in songs:
        if source_key in catalog:
            result.append(source_key)
            continue
        matches = [key for key, (name, _) in catalog.items() if name == title]
        if not matches:
            matches = [key for key, (name, _) in catalog.items() if _normalized_title(name) == _normalized_title(title)]
        if len(matches) != 1:
            issues.append(f"« {title} » ({'absent du carnet' if not matches else 'plusieurs correspondances'})")
        else:
            result.append(matches[0])
    if issues:
        raise ValueError("La liste n'a pas été modifiée. Chants à vérifier : " + "; ".join(issues))
    return result


def verses_from_contents(
    document: str, order: list[str], catalog: dict[str, tuple[str, Path]],
) -> list[list[str] | None]:
    """Restaure les couplets par occurrence ; les anciennes feuilles gardent le choix par défaut."""
    parser = _ContentsParser()
    parser.feed(document)
    if not any(value is not None for value in parser.section_verses):
        return [None for _ in order]
    if len(parser.section_verses) != len(order):
        raise ValueError("La sélection des couplets de cette feuille est incomplète.")
    result = []
    for key, value in zip(order, parser.section_verses):
        if value is None:
            result.append(None)
            continue
        try:
            verses = json.loads(value)
        except (ValueError, TypeError):
            raise ValueError("La sélection des couplets de cette feuille est invalide.") from None
        if (not isinstance(verses, list)
                or any(not isinstance(verse, str) or not re.fullmatch(r"C[1-9]\d*", verse) for verse in verses)
                or len(set(verses)) != len(verses)):
            raise ValueError("La sélection des couplets de cette feuille est invalide.")
        selected_song_parts(catalog[key][1], verses)
        result.append(verses)
    return result
