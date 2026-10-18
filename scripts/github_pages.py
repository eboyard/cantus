"""Prépare des feuilles statiques pour la source GitHub Pages /docs."""

from dataclasses import dataclass
from datetime import date
from html import escape
from io import BytesIO
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit
from zipfile import ZIP_DEFLATED, ZipFile

import qrcode
from qrcode.image.svg import SvgPathFillImage


@dataclass(frozen=True)
class PagesExport:
    path: str
    url: str
    document: bytes
    qr: bytes
    archive: bytes
    parish: str = ""

    @property
    def parish_url(self) -> str:
        return self.url.rstrip("/").rsplit("/", 1)[0] + "/"


def create_parish_index(parish: str, dates: list[str]) -> bytes:
    """Liste les feuilles par date décroissante, avec des liens relatifs."""
    days = sorted({date.fromisoformat(day) for day in dates}, reverse=True)
    links = "\n".join(
        f'<li><a href="{day.isoformat()}/">Feuille du '
        f'<time datetime="{day.isoformat()}">{day.strftime("%d/%m/%Y")}</time></a></li>'
        for day in days
    )
    title = escape(parish)
    listing = f'<ul>{links}</ul>' if days else '<p>Aucune feuille de chants publiée pour le moment.</p>'
    return f'''<!doctype html>
<html lang="fr">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Feuilles de chants — {title}</title>
<style>
body {{ margin: 0; background: #faf9f6; color: #20283b; font: 1.125rem/1.65 system-ui, sans-serif; }}
main {{ max-width: 42rem; margin: auto; padding: 1.25rem; overflow-wrap: anywhere; }}
h1 {{ font-size: 2rem; line-height: 1.2; }}
ul {{ padding-left: 1.5rem; }}
a {{ color: #204a83; text-underline-offset: .2em; }}
li a {{ display: block; padding: .75rem 0; }}
a:focus-visible {{ outline: 3px solid #204a83; outline-offset: 3px; }}
</style></head>
<body><main><h1>{title}</h1><h2>Feuilles de chants</h2>
{listing}
</main></body></html>
'''.encode("utf-8")


def parish_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if not slug or len(slug) > 100:
        raise ValueError("Indiquez un nom de paroisse valide (100 caractères maximum pour l'identifiant).")
    return slug


def prepare_pages_export(document: bytes, parish: str, day: date, base_url: str) -> PagesExport:
    slug = parish_slug(parish)
    parsed = urlsplit(base_url.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Indiquez l'adresse HTTPS du site GitHub Pages, sans paramètres ni fragment.")
    base = urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))
    relative = f"{slug}/{day.isoformat()}"
    url = f"{base}/{relative}/"
    if len(url.encode("utf-8")) > 1000:
        raise ValueError("L'adresse du site est trop longue pour créer un QR code lisible.")
    image = qrcode.make(url, image_factory=SvgPathFillImage, border=4)
    qr_output = BytesIO()
    image.save(qr_output)
    qr = qr_output.getvalue()
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(f"docs/{relative}/index.html", document)
        archive.writestr(f"docs/{relative}/qr.svg", qr)
        archive.writestr("docs/.nojekyll", b"")
    return PagesExport(relative, url, document, qr, output.getvalue(), parish.strip())


def save_pages_export(export: PagesExport, publication_root: Path, *, replace: bool = False) -> Path:
    root = publication_root.resolve()
    target = (root / export.path / "index.html").resolve()
    if not target.is_relative_to(root):
        raise ValueError("Le chemin de publication doit rester dans le dossier du site.")
    if target.exists() and not replace:
        raise ValueError("Une feuille existe déjà pour cette paroisse et cette date. Cochez le remplacement pour la mettre à jour.")
    parish_index = (target.parent.parent / "index.html").resolve()
    if not parish_index.is_relative_to(root):
        raise ValueError("Le chemin de publication doit rester dans le dossier du site.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(export.document)
    target.with_name("qr.svg").write_bytes(export.qr)
    (root / ".nojekyll").touch()
    dates = [entry.parent.name for entry in target.parent.parent.glob("????-??-??/index.html")
             if _valid_date(entry.parent.name)]
    parish_index.write_bytes(
        create_parish_index(export.parish or target.parent.parent.name, dates)
    )
    return target


def _valid_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False
