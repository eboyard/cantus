"""Prépare des feuilles statiques pour la source GitHub Pages /docs."""

from dataclasses import dataclass
from datetime import date
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
    return PagesExport(relative, url, document, qr, output.getvalue())


def save_pages_export(export: PagesExport, publication_root: Path, *, replace: bool = False) -> Path:
    root = publication_root.resolve()
    target = (root / export.path / "index.html").resolve()
    if not target.is_relative_to(root):
        raise ValueError("Le chemin de publication doit rester dans le dossier du site.")
    if target.exists() and not replace:
        raise ValueError("Une feuille existe déjà pour cette paroisse et cette date. Cochez le remplacement pour la mettre à jour.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(export.document)
    target.with_name("qr.svg").write_bytes(export.qr)
    (root / ".nojekyll").touch()
    return target
