"""Publie une feuille HTML via l'API Contents de GitHub."""

import base64
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from scripts.github_pages import PagesExport


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


def publish_sheet(export: PagesExport, token: str, *, repository: str = "eboyard/cantus", branch: str = "main", replace: bool = False) -> str:
    """Crée un commit pour index.html ; le SHA empêche les écrasements concurrents."""
    if not token.strip():
        raise GitHubPublishError("Le jeton GitHub n'est pas configuré dans les secrets Streamlit.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or not branch.strip():
        raise GitHubPublishError("La configuration du dépôt ou de la branche GitHub est invalide.")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*/\d{4}-\d{2}-\d{2}", export.path):
        raise GitHubPublishError("Le chemin de publication est invalide.")
    path = f"docs/{export.path}/index.html"
    endpoint = f"https://api.github.com/repos/{repository}/contents/{quote(path, safe='/')}"
    try:
        try:
            existing = _request("GET", endpoint + "?" + urlencode({"ref": branch}), token)
        except HTTPError as error:
            if error.code != 404:
                raise
            existing = None
        if existing is not None and not replace:
            raise GitHubPublishError("Une feuille existe déjà pour cette paroisse et cette date. Cochez le remplacement pour la mettre à jour.")
        payload = {
            "message": f"Publier la feuille de chants {export.path}",
            "content": base64.b64encode(export.document).decode("ascii"),
            "branch": branch,
        }
        if existing is not None:
            if not isinstance(existing.get("sha"), str) or existing.get("type") != "file":
                raise GitHubPublishError("Le chemin sur GitHub ne correspond pas à un fichier remplaçable.")
            payload["sha"] = existing["sha"]
        result = _request("PUT", endpoint, token, payload)
        commit = result.get("commit")
        sha = commit.get("sha") if isinstance(commit, dict) else None
        if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40,64}", sha):
            raise GitHubPublishError("GitHub n'a pas confirmé le commit. Vérifiez le dépôt avant de réessayer.")
        return f"https://github.com/{repository}/commit/{sha}"
    except HTTPError as error:
        messages = {
            401: "Le jeton GitHub est invalide ou expiré.",
            403: "Accès refusé par GitHub. Vérifiez les droits Contents: Read and write, les règles du dépôt et les limites d'accès.",
            404: "Dépôt ou branche introuvable, ou jeton sans accès au dépôt configuré.",
            409: "Le fichier a changé pendant la publication. Vérifiez la version en ligne avant de réessayer.",
            422: "GitHub refuse cette publication. Vérifiez la branche, les règles du dépôt et l'existence du fichier.",
        }
        raise GitHubPublishError(messages.get(error.code, "La publication a échoué côté GitHub. Vérifiez le dépôt avant de réessayer.")) from None
