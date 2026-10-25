"""Extrait le texte des partitions PDF vers des fichiers .txt (brouillons pour chants/)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pymupdf

# Syllabes séparées sous la portée : "Ve - nez" / "Ve- nez" / "Ve -nez" -> "Venez"
SYLLABLE_SPLIT = re.compile(r"(\w)\s*[-–_]+\s+(?=\w)|(\w)\s+[-–_]+\s*(?=\w)")
SPACES = re.compile(r"[ \t]+")


def clean_text(raw: str) -> str:
    lines = []
    for line in raw.splitlines():
        line = SYLLABLE_SPLIT.sub(lambda m: m.group(1) or m.group(2), line)
        line = SPACES.sub(" ", line).strip()
        if line or (lines and lines[-1]):
            lines.append(line)
    return "\n".join(lines).strip() + "\n"


def page_text(page: pymupdf.Page, ocr: bool) -> str:
    if ocr:  # nécessite Tesseract installé (pack de langue "fra")
        textpage = page.get_textpage_ocr(language="fra", dpi=300, full=True)
        return page.get_text("text", sort=True, textpage=textpage)
    return page.get_text("text", sort=True)


def extract_pdf(path: Path, raw: bool = False, ocr: bool = False) -> str:
    with pymupdf.open(path) as doc:
        text = "\n".join(page_text(page, ocr) for page in doc)
    return text if raw else clean_text(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default="temp", type=Path, help="PDF ou dossier de PDF (défaut: temp)")
    parser.add_argument("-o", "--output-dir", default=Path("temp/textes"), type=Path)
    parser.add_argument("--raw", action="store_true", help="texte brut, sans recoller les syllabes")
    parser.add_argument("--overwrite", action="store_true", help="réécrit les .txt existants")
    parser.add_argument("--ocr", action="store_true", help="OCR Tesseract (pour les PDF scannés)")
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    pdfs = [args.source] if args.source.is_file() else sorted(args.source.glob("*.pdf"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    empty = []
    for pdf in pdfs:
        target = args.output_dir / f"{pdf.stem}.txt"
        if target.exists() and not args.overwrite:
            continue
        try:
            text = extract_pdf(pdf, args.raw, args.ocr)
        except Exception as exc:  # PDF corrompu : on continue avec les autres
            print(f"ERREUR {pdf.name}: {exc}", file=sys.stderr)
            continue
        if not text.strip():
            empty.append(pdf.name)
            continue
        target.write_text(text, encoding="utf-8")
        print(f"ok  {pdf.name}")

    if empty:
        print(f"\n{len(empty)} PDF sans texte (scans, OCR nécessaire) :")
        for name in empty:
            print(f"  - {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
