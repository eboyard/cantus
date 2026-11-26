"""Prépare des feuilles statiques pour la source GitHub Pages /docs."""

from base64 import b64encode
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


def create_parish_index(parish: str, dates: list[str], *, parish_url: str | None = None) -> bytes:
    """Affiche la prochaine feuille selon la date locale du navigateur."""
    days = sorted({date.fromisoformat(day) for day in dates}, reverse=True)
    parish_url = parish_url or f"https://eboyard.github.io/cantus/{parish_slug(parish)}/"
    items = []
    for day in days:
        iso = day.isoformat()
        label = day.strftime("%d/%m/%Y")
        qr = b64encode(_create_qr(f"{parish_url.rstrip('/')}/{iso}/")).decode("ascii")
        image_url = f"data:image/svg+xml;base64,{qr}"
        items.append(
            f'<li data-date="{iso}"><a href="{iso}/">Feuille du '
            f'<time datetime="{iso}">{label}</time></a>'
            f'<details><summary title="Afficher le QR code de la feuille du {label}">'
            '<svg class="qr-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
            '<path fill="currentColor" d="M2 2h8v8H2zm2 2v4h4V4zM14 2h8v8h-8zm2 2v4h4V4z'
            'M2 14h8v8H2zm2 2v4h4v-4zM12 12h4v4h-4zm6 0h4v2h-4zM18 16h2v4h-4v-2h2z'
            'M12 18h2v4h-2zM20 20h2v2h-2z"/></svg>'
            f'<span class="sr-only">Afficher le QR code de la feuille du {label}</span></summary>'
            f'<div class="qr-code"><img src="{image_url}" width="280" height="280" '
            f'alt="QR code vers la feuille de chants du {label}" loading="lazy">'
            f'<a href="{image_url}" download="qr-{iso}.svg">Télécharger le QR code (SVG)</a>'
            f'</div></details></li>'
        )
    links = "\n".join(items)
    title = escape(parish)
    listing = f'''<nav id="sheet-navigation" aria-label="Choisir une feuille de chants" hidden>
<label for="sheet-date">Feuille de chants de la célébration du</label>
<div class="date-navigation">
<select id="sheet-date"></select>
<div class="navigation-buttons">
<button id="previous-sheet" type="button" aria-label="Feuille précédente" title="Feuille précédente">
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m14 6-6 6 6 6"/></svg></button>
<button id="next-sheet" type="button" aria-label="Feuille suivante" title="Feuille suivante">
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m10 6 6 6-6 6"/></svg></button>
<button id="home-sheet" type="button" aria-label="Revenir à la feuille proposée" title="Revenir à la feuille proposée">
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m3 10 9-7 9 7M5 9v12h5v-7h4v7h5V9"/></svg></button>
</div></div>
</nav>
<p id="sheet-status" role="status" hidden></p>
<ul id="sheets">{links}</ul>
<iframe id="sheet-content" title="Feuille de chants" hidden></iframe>''' if days else '<p>Aucune feuille de chants publiée pour le moment.</p>'
    return f'''<!doctype html>
<html lang="fr">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Feuilles de chants — {title}</title>
<style>
body {{ margin: 0; background: #faf9f6; color: #20283b; font: 1.125rem/1.65 system-ui, sans-serif; }}
main {{ max-width: 42rem; margin: auto; padding: 1.25rem; overflow-wrap: anywhere; }}
h1 {{ font-size: 2rem; line-height: 1.2; }}
ul {{ list-style: none; padding: 0; }}
a {{ color: #204a83; text-underline-offset: .2em; }}
li {{ position: relative; padding: .2rem 3.25rem .2rem 0; }}
li > a {{ display: inline-block; padding: .45rem 0; }}
summary {{ position: absolute; top: .2rem; right: 0; display: flex; align-items: center; justify-content: center; width: 2.75rem; height: 2.75rem; box-sizing: border-box; color: #204a83; cursor: pointer; border: 1px solid #d4d9e1; border-radius: .4rem; list-style: none; }}
summary::-webkit-details-marker {{ display: none; }}
summary:hover, details[open] > summary {{ background: #e9eef5; }}
.qr-icon {{ width: 1.4rem; height: 1.4rem; }}
.qr-code {{ margin-top: .5rem; }}
.qr-code img {{ display: block; width: 280px; max-width: 100%; height: auto; background: white; }}
.qr-code a {{ display: inline-block; padding: .5rem 0; }}
.sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }}
summary:focus-visible {{ outline: 3px solid #204a83; outline-offset: 3px; }}
a:focus-visible {{ outline: 3px solid #204a83; outline-offset: 3px; }}
[hidden] {{ display: none !important; }}
button, select {{ font: inherit; color: #204a83; background: white; border: 1px solid #b5bfce; border-radius: .4rem; padding: .6rem .8rem; min-height: 2.75rem; }}
button {{ cursor: pointer; }}
button:disabled {{ opacity: .5; cursor: default; }}
button:focus-visible, select:focus-visible {{ outline: 3px solid #204a83; outline-offset: 3px; }}
#sheet-navigation {{ display: grid; gap: .6rem; }}
.date-navigation {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: .5rem; }}
#sheet-date {{ min-width: 0; width: 100%; box-sizing: border-box; }}
.navigation-buttons {{ display: flex; gap: .25rem; }}
.navigation-buttons button {{ display: inline-flex; align-items: center; justify-content: center; width: 2.75rem; height: 2.75rem; padding: .5rem; border-color: transparent; background: transparent; }}
.navigation-buttons button:hover:not(:disabled) {{ background: #e9eef5; }}
.navigation-buttons svg {{ width: 1.25rem; height: 1.25rem; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }}
#sheet-status {{ font-weight: 600; margin-bottom: .25rem; }}
#sheet-content {{ display: block; width: 100%; height: 75vh; border: 0; background: white; }}
#sheets {{ border: 1px solid #d4d9e1; border-radius: .5rem; padding: .5rem .75rem; }}
</style></head>
<body><main><h1>{title}</h1>
{listing}
</main><script>{_PARISH_NAVIGATION}</script></body></html>
'''.encode("utf-8")


_PARISH_NAVIGATION = r'''
(() => {
  const sheets = Array.from(document.querySelectorAll('#sheets > li')).reverse();
  if (!sheets.length) return;
  const previous = document.getElementById('previous-sheet');
  const next = document.getElementById('next-sheet');
  const home = document.getElementById('home-sheet');
  const select = document.getElementById('sheet-date');
  const status = document.getElementById('sheet-status');
  const frame = document.getElementById('sheet-content');
  // Compare calendar dates in the visitor's timezone, including the entire day.
  const now = new Date();
  const today = [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0')].join('-');
  const upcoming = sheets.findIndex(sheet => sheet.dataset.date >= today);
  const recommended = upcoming < 0 ? sheets.length - 1 : upcoming;
  const formatter = new Intl.DateTimeFormat('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  });
  const labels = sheets.map(sheet => {
    const [year, month, day] = sheet.dataset.date.split('-').map(Number);
    const label = formatter.format(new Date(year, month - 1, day));
    const option = document.createElement('option');
    option.value = sheet.dataset.date;
    option.textContent = label;
    select.appendChild(option);
    return label;
  });
  let selected = recommended;
  function show(index) {
    selected = index;
    sheets.forEach((sheet, i) => {
      sheet.hidden = i !== selected;
      if (i !== selected) sheet.querySelector('details').open = false;
    });
    const day = sheets[selected].dataset.date;
    select.value = day;
    previous.disabled = selected === 0;
    next.disabled = selected === sheets.length - 1;
    home.disabled = selected === recommended;
    status.textContent = upcoming < 0 ? 'Aucune feuille à venir publiée pour le moment.' : '';
    status.hidden = upcoming >= 0;
    frame.title = 'Feuille de chants du ' + labels[selected];
    frame.src = sheets[selected].querySelector('a').getAttribute('href');
  }
  previous.addEventListener('click', () => { if (selected > 0) show(selected - 1); });
  next.addEventListener('click', () => { if (selected < sheets.length - 1) show(selected + 1); });
  home.addEventListener('click', () => show(recommended));
  select.addEventListener('change', () => show(sheets.findIndex(sheet => sheet.dataset.date === select.value)));
  show(recommended);
  document.getElementById('sheet-navigation').hidden = false;
  frame.hidden = false;
})();
'''


def parish_slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    if not slug or len(slug) > 100:
        raise ValueError("Indiquez un nom de paroisse valide (100 caractères maximum pour l'identifiant).")
    return slug


def _create_qr(url: str) -> bytes:
    image = qrcode.make(url, image_factory=SvgPathFillImage, border=4)
    output = BytesIO()
    image.save(output)
    return output.getvalue()


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
    qr = _create_qr(url)
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
        create_parish_index(export.parish or target.parent.parent.name, dates, parish_url=export.parish_url)
    )
    return target


def _valid_date(value: str) -> bool:
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False
