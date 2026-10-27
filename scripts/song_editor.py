"""Formulaire de chant et mise à jour d'un fichier existant sur GitHub."""

import base64
from dataclasses import dataclass
import json
import re
from urllib.error import HTTPError
from urllib.parse import quote, urlencode

from scripts.github_publish import GitHubPublishError, _request, _sha
from scripts.markdown_to_pptx import METADATA_TAG, TITLE_TAG, build_slides


@dataclass(frozen=True)
class SongDraft:
    title: str
    lyrics: str
    author: str = ""
    chords: str = ""
    key: str = ""
    information: str = ""


def parse_song(document: str, fallback_title: str = "") -> SongDraft:
    title = TITLE_TAG.search(document)
    metadata = {}
    for marker in METADATA_TAG.finditer(document):
        value = marker[2].strip()
        try:
            decoded = json.loads(value)
            if isinstance(decoded, str):
                value = decoded
        except ValueError:
            pass
        metadata[marker[1].lower()] = value
    return SongDraft(
        title[1].strip() if title else fallback_title,
        METADATA_TAG.sub("", TITLE_TAG.sub("", document)).strip(),
        metadata.get("auteur", ""), metadata.get("accords", ""),
        metadata.get("tonalite", ""), metadata.get("informations", ""),
    )


def serialize_song(draft: SongDraft) -> str:
    if not draft.title.strip() or any(c in draft.title for c in ("\n", "\r", "<!--", "-->")):
        raise ValueError("Le titre doit tenir sur une ligne et ne peut pas contenir de commentaire HTML.")
    # Les métadonnées sont des commentaires invisibles dans les exports.
    lines = [f"<!-- titre: {draft.title.strip()} -->"]
    for name, value in (("auteur", draft.author), ("accords", draft.chords),
                        ("tonalite", draft.key), ("informations", draft.information)):
        if "<!--" in value or "-->" in value:
            raise ValueError("Les informations du chant ne peuvent pas contenir de commentaire HTML.")
        if value.strip():
            lines.append(f"<!-- {name}: {json.dumps(value.strip(), ensure_ascii=False)} -->")
    if TITLE_TAG.search(draft.lyrics) or METADATA_TAG.search(draft.lyrics):
        raise ValueError("Renseignez le titre et les informations dans leurs champs dédiés.")
    document = "\n".join(lines) + "\n\n" + draft.lyrics.strip() + "\n"
    if not any(slide.strip() for slide in build_slides(document)):
        raise ValueError("Les paroles ne peuvent pas être vides.")
    return document


def _endpoint(repository: str, branch: str, path: str, token: str) -> str:
    if not token.strip():
        raise GitHubPublishError("Le jeton GitHub n'est pas configuré.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not branch.strip():
        raise GitHubPublishError("La configuration du dépôt ou de la branche est invalide.")
    if (not path.startswith("chants/") or not path.endswith(".md")
            or any(part in ("", ".", "..") for part in path.split("/")) or "\\" in path):
        raise GitHubPublishError("Seuls les fichiers Markdown du carnet peuvent être modifiés.")
    return f"https://api.github.com/repos/{repository}/contents/{quote(path, safe='/')}"


def _api(method: str, endpoint: str, token: str, payload=None) -> dict:
    try:
        return _request(method, endpoint, token, payload)
    except HTTPError as error:
        message = {
            401: "Le jeton GitHub est invalide ou expiré.",
            403: "GitHub refuse l'accès. Vérifiez les droits Contents: Read and write et les règles du dépôt.",
            404: "Chant, dépôt ou branche introuvable, ou jeton sans accès.",
            409: "Le chant a changé sur GitHub. Conservez vos modifications puis annulez et rouvrez l'éditeur pour les reporter sur la dernière version.",
            422: "GitHub refuse la modification. Vérifiez les règles de la branche et la dernière version du chant.",
        }.get(error.code, "Échec GitHub. Vérifiez le dépôt avant de réessayer.")
        raise GitHubPublishError(message) from None


def load_song(token: str, repository: str, branch: str, path: str) -> tuple[str, str]:
    endpoint = _endpoint(repository, branch, path, token)
    result = _api("GET", endpoint + "?" + urlencode({"ref": branch}), token)
    if result.get("type") != "file" or result.get("encoding") != "base64" or "target" in result:
        raise GitHubPublishError("GitHub n'a pas fourni un fichier texte modifiable.")
    try:
        document = base64.b64decode("".join(result["content"].split()), validate=True).decode("utf-8-sig")
    except (KeyError, TypeError, AttributeError, ValueError, UnicodeError):
        raise GitHubPublishError("Le chant GitHub n'est pas un texte UTF-8 valide.") from None
    return document, _sha(result.get("sha"))


def save_song(token: str, repository: str, branch: str, path: str,
              document: str, expected_sha: str) -> str:
    endpoint = _endpoint(repository, branch, path, token)
    result = _api("PUT", endpoint, token, {
        "message": f"Modifier le chant {parse_song(document).title}",
        "content": base64.b64encode(document.encode("utf-8")).decode("ascii"),
        "sha": _sha(expected_sha), "branch": branch,
    })
    commit = result.get("commit")
    sha = _sha(commit.get("sha") if isinstance(commit, dict) else None)
    return f"https://github.com/{repository}/commit/{sha}"
