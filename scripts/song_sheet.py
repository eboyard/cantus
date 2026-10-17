"""Crée une feuille de chants HTML autonome, adaptée aux téléphones."""

from html import escape
from pathlib import Path

from scripts.markdown_to_pptx import read_slides, styled_lines


def create_song_sheet(title: str, songs: list[tuple[str, Path]]) -> bytes:
    """Conserve l'ordre des chants, l'alternance des parties et le gras."""
    if not songs:
        raise ValueError("Ajoutez au moins un chant pour créer la feuille.")
    contents = []
    sections = []
    for position, (song_title, path) in enumerate(songs, start=1):
        blocks = read_slides(path)
        if not blocks:
            raise ValueError(f"Le chant {path.name} ne contient aucune parole.")
        song_id = f"chant-{position}"
        contents.append(f'<li><a href="#{song_id}">{escape(song_title)}</a></li>')
        lyrics = []
        for block in blocks:
            lines = []
            for line in styled_lines(block):
                lines.append("".join(
                    f"<strong>{escape(text)}</strong>" if bold else escape(text)
                    for text, bold in line
                ))
            lyrics.append('<p class="paroles">' + "<br>\n".join(lines) + "</p>")
        sections.append(
            f'<section id="{song_id}" aria-labelledby="titre-{position}">'
            f'<h2 id="titre-{position}">{position}. {escape(song_title)}</h2>'
            + "\n".join(lyrics)
            + '<a class="retour" href="#sommaire">Retour au sommaire ↑</a></section>'
        )
    page_title = escape(title.strip() or "Messe")
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
h2 {{ font-size: 1.5rem; line-height: 1.3; }}
a {{ color: #204a83; text-underline-offset: .2em; }}
a:focus-visible {{ outline: 3px solid #204a83; outline-offset: 3px; }}
nav {{ margin: 2rem 0; padding: 1rem; border: 1px solid #d9deea; border-radius: .75rem; }}
nav h2 {{ margin-top: 0; }}
ol {{ padding-left: 1.75rem; margin-bottom: 0; }}
li a {{ display: block; padding: .5rem 0; }}
section {{ margin-top: 2.5rem; padding-top: 1rem; border-top: 2px solid #d9deea; }}
.paroles {{ margin: 1.5rem 0; }}
.retour {{ display: inline-block; padding: .75rem 0; font-size: 1rem; }}
.sous-titre {{ margin-top: 0; color: #596176; }}
@media print {{ body {{ background: white; font-size: 12pt; }}
                nav, .retour {{ display: none; }} .paroles {{ break-inside: avoid; }} }}
</style>
</head>
<body><main>
<header><h1>{page_title}</h1><p class="sous-titre">Feuille de chants</p></header>
<nav id="sommaire" aria-label="Sommaire des chants"><h2>Les chants</h2>
<ol>{''.join(contents)}</ol></nav>
{''.join(sections)}
</main></body>
</html>
"""
    return document.encode("utf-8")
