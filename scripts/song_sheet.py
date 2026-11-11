"""Crée une feuille de chants HTML autonome, adaptée aux téléphones."""

from datetime import date
from html import escape
from pathlib import Path

from scripts.song_selection import selected_song_parts
from scripts.lyrics_format import formatted_lines, fragment_html
from scripts.song_types import MOMENTS, celebration_moments, read_song_type


IMPLICIT_MOMENTS = frozenset({
    "Gloire à Dieu", "Psaume", "Acclamation de l’Évangile", "Sanctus", "Agneau de Dieu",
})


def create_song_sheet(
    title: str, songs: list[tuple[str, Path]], *, day: date | None = None,
    moments: list[str] | None = None,
    verses: list[list[str] | None] | None = None,
) -> bytes:
    """Conserve l'ordre des chants, l'alternance des parties et le gras."""
    if not songs:
        raise ValueError("Ajoutez au moins un chant pour créer la feuille.")
    if moments is None:
        moments = [read_song_type(path) for _, path in songs]
    if len(moments) != len(songs) or any(moment not in ("", *MOMENTS) for moment in moments):
        raise ValueError("Choisissez une rubrique valide pour chaque chant.")
    moments = celebration_moments(moments)
    if verses is not None and len(verses) != len(songs):
        raise ValueError("Choisissez les couplets pour chaque chant.")
    sections = []
    for position, (song_title, path) in enumerate(songs, start=1):
        blocks = [part.text for part in selected_song_parts(path, None if verses is None else verses[position - 1])]
        if not blocks:
            raise ValueError(f"Le chant {path.name} ne contient aucune parole.")
        song_id = f"chant-{position}"
        try:
            song_key = path.resolve().relative_to(Path(__file__).resolve().parents[1]).as_posix()
        except ValueError:
            song_key = ""
        source = f' data-song-key="{escape(song_key, quote=True)}"' if song_key else ""
        lyrics = []
        for block in blocks:
            lines = []
            for line in formatted_lines(block):
                lines.append("".join(
                    fragment_html(fragment).replace("<b>", "<strong>").replace("</b>", "</strong>")
                    for fragment in line
                ))
            lyrics.append('<p class="paroles">' + "<br>\n".join(lines) + "</p>")
        moment = moments[position - 1]
        rubrique = f'<p class="moment">{escape(moment)}</p>' if moment and moment not in IMPLICIT_MOMENTS else ""
        sections.append(
            f'<section id="{song_id}" aria-labelledby="titre-{position}"{source}>'
            + rubrique
            + f'<h2 id="titre-{position}">{escape(song_title)}</h2>'
            + "\n".join(lyrics)
            + '</section>'
        )
    heading = title.strip() or "Messe"
    if day is not None:
        heading += f" — {day.strftime('%d/%m/%Y')}"
    page_title = escape(heading)
    document = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title} — Feuille de chants</title>
<style>
* {{ box-sizing: border-box; }}
html {{ scroll-padding-top: 1rem; }}
body {{ margin: 0; background: #faf9f6; color: #20283b;
       font: 1.125rem/1.65 system-ui, sans-serif; overflow-wrap: anywhere; }}
main {{ max-width: 42rem; margin: auto; padding: 1.25rem; }}
h1 {{ font-size: 2rem; line-height: 1.2; margin-bottom: .5rem; }}
h2, .moment {{ font-size: 1.5rem; line-height: 1.3; }}
section {{ margin-top: 2.5rem; padding-top: 1rem; border-top: 2px solid #d9deea; }}
.moment {{ margin: 0 0 .5rem; color: #596176; font-weight: 700; }}
.moment + h2 {{ margin-top: 0; }}
.paroles {{ margin: 1.5rem 0; }}
.sous-titre {{ margin-top: 0; color: #596176; }}
@media print {{ body {{ background: white; font-size: 12pt; }}
                .paroles {{ break-inside: avoid; }} }}
</style>
</head>
<body><main>
<header><h1>{page_title}</h1><p class="sous-titre">Feuille de chants</p></header>
{''.join(sections)}
</main></body>
</html>
"""
    return document.encode("utf-8")
