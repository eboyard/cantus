#!/usr/bin/env python3
"""Extraction locale de PDF en UTF-8, avec nettoyage optionnel des partitions."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pdfplumber


MUSIC_FONTS = ("anastasia", "maestro", "petrucci", "opus", "bravura", "emmentaler")
CHORD = re.compile(r"[A-G](?:[#b♯♭])?(?:m|maj|min|dim|aug|sus|add)?\d*(?:/[A-G][#b♯♭]?)?")


def clean_lyrics(text: str) -> str:
    """Réunit les syllabes explicites, sans corriger ni inventer les mots."""
    # Un tiret isolé représente souvent la prolongation d'une note :
    # « Dieu - vi- vant » devient « Dieu vivant », pas « Dieuvivant ».
    text = re.sub(r"(?<!\S)[-–](?!\S)", "", text)
    text = re.sub(r"(?<=\w)-[ \t]+(?=\w)", "", text)
    text = re.sub(r"[ \t]+([,.;!?])", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text).strip()
    # Typographie française ; espaces ordinaires pour faciliter la réutilisation.
    return re.sub(r"(?<=\w)([;!?])", r" \1", text)


def is_chord_line(text: str) -> bool:
    tokens = text.split()
    # Une altération peut utiliser la police musicale, filtrée séparément,
    # et laisser « F m » à la place de « F#m ».
    return bool(tokens) and all(CHORD.fullmatch(t) or t in {"m", "#", "b", "♯", "♭"} for t in tokens)


def native_text(page, mode: str, extra_fonts: list[str]) -> str:
    if mode == "text":
        return page.extract_text(x_tolerance=1) or ""
    excluded = MUSIC_FONTS + tuple(f.casefold() for f in extra_fonts)
    filtered = page.filter(
        lambda obj: obj.get("object_type") != "char"
        or not any(f in obj.get("fontname", "").casefold() for f in excluded)
    )
    text = filtered.extract_text(x_tolerance=1) or ""
    return "\n".join(
        clean_lyrics(line)
        for line in text.splitlines()
        if line.strip() and not is_chord_line(line) and not line.strip().isdigit()
    )


def ocr_page(page, language: str, dpi: int) -> str:
    try:
        import pytesseract
        from pytesseract import TesseractError, TesseractNotFoundError
    except ImportError as exc:
        raise RuntimeError(
            "OCR requis : installer pytesseract et Tesseract avec la langue " + language
        ) from exc
    try:
        image = page.to_image(resolution=dpi).original
        try:
            return pytesseract.image_to_string(image, lang=language, config="--psm 3").strip()
        finally:
            image.close()
    except (TesseractError, TesseractNotFoundError) as exc:
        raise RuntimeError(f"OCR indisponible ou en échec : {exc}") from exc


def extract(path: Path, mode: str, ocr: str, language: str, dpi: int,
            extra_fonts: list[str]) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            text = native_text(page, mode, extra_fonts)
            if ocr == "always" or (ocr == "auto" and not text.strip()):
                print(f"{path.name}, page {number} : OCR", file=sys.stderr)
                text = ocr_page(page, language, dpi)
                if mode == "partition":
                    text = "\n".join(clean_lyrics(line) for line in text.splitlines()
                                     if line.strip() and not is_chord_line(line))
                print("L'OCR peut confondre les notes et les lettres ; vérifier le résultat.",
                      file=sys.stderr)
            if not text.strip():
                print(f"{path.name}, page {number} : aucun texte exploitable.", file=sys.stderr)
                text = f"[Page {number} : aucun texte extrait]"
            if "\ufffd" in text or "(cid:" in text:
                print(f"{path.name}, page {number} : caractères non décodés ; "
                      "essayer --ocr always et vérifier le résultat.", file=sys.stderr)
            pages.append(text)
    return "\n\n\f\n\n".join(pages) + "\n"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="PDF ou dossiers de PDF (sans récursion)")
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("output/text"))
    parser.add_argument("--mode", choices=("text", "partition"), default="text")
    parser.add_argument("--ocr", choices=("never", "auto", "always"), default="auto",
                        help="auto : OCR uniquement si aucun texte n'a été extrait")
    parser.add_argument("--language", default="fra", help="Langues Tesseract, ex. fra+eng")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--exclude-font", action="append", default=[],
                        help="Fragment de nom de police musicale à exclure ; répétable")
    parser.add_argument("--force", action="store_true", help="Remplacer les TXT déjà présents")
    args = parser.parse_args()
    if not 72 <= args.dpi <= 600:
        parser.error("--dpi doit être compris entre 72 et 600")
    paths = []
    for source in args.inputs:
        if source.is_dir():
            paths.extend(sorted(p for p in source.iterdir() if p.suffix.lower() == ".pdf"))
        else:
            paths.append(source)
    paths = list(dict.fromkeys(p.resolve() for p in paths))
    if not paths:
        parser.error("Aucun PDF trouvé")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    failed = False
    targets = set()
    for path in paths:
        try:
            if not path.is_file() or path.suffix.lower() != ".pdf":
                raise ValueError(f"PDF introuvable ou extension incorrecte : {path}")
            target = args.output_dir / (path.stem + ".txt")
            key = str(target.resolve()).casefold()
            if key in targets:
                raise ValueError(f"Deux PDF produiraient le même fichier : {target}")
            targets.add(key)
            if target.exists() and not args.force:
                raise FileExistsError(f"{target} existe déjà ; utiliser --force pour le remplacer")
            result = extract(path, args.mode, args.ocr, args.language, args.dpi, args.exclude_font)
            with target.open("w" if args.force else "x", encoding="utf-8", newline="\n") as output:
                output.write(result)
            print(f"Texte extrait : {target.resolve()}")
        except Exception as exc:
            print(f"Erreur : {path} : {exc}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
