"""Publie une feuille et son index paroissial dans un même commit GitHub."""

import json
import re
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from scripts.github_pages import PagesExport, create_parish_index


class GitHubPublishError(ValueError):
    """Erreur affichable sans exposer le jeton ni la réponse brute de GitHub."""


def _request(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    request = Request(
        url, method=method,
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2026-03-10",
            "User-Agent": "cantus-song-sheets",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise GitHubPublishError("Réponse inattendue de GitHub. Vérifiez le dépôt avant de réessayer.")
        return result
    except HTTPError:
        raise
    except (URLError, TimeoutError, OSError):
        raise GitHubPublishError("GitHub est injoignable. Vérifiez le dépôt avant de réessayer : l'envoi a peut-être abouti.") from None
    except (ValueError, UnicodeError):
        raise GitHubPublishError("Réponse inattendue de GitHub. Vérifiez le dépôt avant de réessayer.") from None


def _sha(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{40,64}", value):
        raise GitHubPublishError("GitHub n'a pas confirmé le commit. Vérifiez le dépôt avant de réessayer.")
    return value


def _nested_sha(result: dict, key: str) -> str:
    value = result.get(key)
    return _sha(value.get("sha") if isinstance(value, dict) else None)


def publish_sheet(export: PagesExport, token: str, *, repository: str = "eboyard/cantus", branch: str = "main", replace: bool = False) -> str:
    """Publie ensemble la feuille et l'index, sans écraser les commits concurrents."""
    if not token.strip():
        raise GitHubPublishError("Le jeton GitHub n'est pas configuré dans les secrets Streamlit.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not branch.strip():
        raise GitHubPublishError("La configuration du dépôt ou de la branche GitHub est invalide.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*/\d{4}-\d{2}-\d{2}", export.path):
        raise GitHubPublishError("Le chemin de publication est invalide.")
    path = f"docs/{export.path}/index.html"
    slug, day = export.path.split("/")
    date.fromisoformat(day)
    endpoint = f"https://api.github.com/repos/{repository}/git"
    ref = "heads/" + quote(branch, safe="/")
    try:
        reference = _request("GET", f"{endpoint}/ref/{ref}", token)
        parent = _nested_sha(reference, "object")
        commit = _request("GET", f"{endpoint}/commits/{parent}", token)
        base_tree = _nested_sha(commit, "tree")
        tree = _request("GET", f"{endpoint}/trees/{base_tree}?recursive=1", token)
        if tree.get("truncated") is not False or not isinstance(tree.get("tree"), list):
            raise GitHubPublishError("GitHub n'a pas fourni la liste complète des feuilles. Publication annulée pour préserver l'index.")
        if any(not isinstance(entry, dict) or not isinstance(entry.get("path"), str) for entry in tree["tree"]):
            raise GitHubPublishError("Réponse inattendue de GitHub. Vérifiez le dépôt avant de réessayer.")
        entries = {entry["path"]: entry for entry in tree["tree"]}
        existing = entries.get(path)
        if existing is not None and not replace:
            raise GitHubPublishError("Une feuille existe déjà pour cette paroisse et cette date. Cochez le remplacement pour la mettre à jour.")
        if existing is not None and (existing.get("type") != "blob" or existing.get("mode") not in ("100644", "100755")):
            raise GitHubPublishError("Le chemin sur GitHub ne correspond pas à un fichier remplaçable.")
        dates = {day}
        for name, entry in entries.items():
            match = re.fullmatch(rf"docs/{re.escape(slug)}/(\d{{4}}-\d{{2}}-\d{{2}})/index\.html", name)
            if match and entry.get("type") == "blob" and entry.get("mode") in ("100644", "100755"):
                try:
                    dates.add(date.fromisoformat(match[1]).isoformat())
                except ValueError:
                    continue
        files = {
            path: export.document.decode("utf-8"),
            f"docs/{slug}/index.html": create_parish_index(export.parish or slug, list(dates)).decode("utf-8"),
            "docs/.nojekyll": "",
        }
        new_tree = _request("POST", f"{endpoint}/trees", token, {
            "base_tree": base_tree,
            "tree": [{"path": name, "mode": "100644", "type": "blob", "content": content}
                     for name, content in files.items()],
        })
        result = _request("POST", f"{endpoint}/commits", token, {
            "message": f"Publier la feuille de chants {export.path}",
            "tree": _sha(new_tree.get("sha")), "parents": [parent],
        })
        sha = _sha(result.get("sha"))
        updated = _request("PATCH", f"{endpoint}/refs/{ref}", token, {"sha": sha, "force": False})
        if _nested_sha(updated, "object") != sha:
            raise GitHubPublishError("GitHub n'a pas confirmé la publication. Vérifiez le dépôt avant de réessayer.")
        return f"https://github.com/{repository}/commit/{sha}"
    except HTTPError as error:
        messages = {
            401: "Le jeton GitHub est invalide ou expiré.",
            403: "Accès refusé par GitHub. Vérifiez les droits Contents: Read and write, les règles du dépôt et les limites d'accès.",
            404: "Dépôt ou branche introuvable, ou jeton sans accès au dépôt configuré.",
            409: "La branche a changé pendant la publication. Préparez à nouveau la feuille puis réessayez.",
            422: "GitHub refuse cette publication. La branche a peut-être changé : réessayez après vérification des règles du dépôt.",
        }
        raise GitHubPublishError(messages.get(error.code, "La publication a échoué côté GitHub. Vérifiez le dépôt avant de réessayer.")) from None
