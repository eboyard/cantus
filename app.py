"""Interface Streamlit pour preparer un diaporama de chants."""

from __future__ import annotations

import os
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import quote

import streamlit as st

from scripts.markdown_to_pptx import convert, read_slides


ROOT = Path(__file__).resolve().parent
SONGS_DIR = ROOT / "chants"


def song_catalog() -> dict[str, tuple[str, Path]]:
    catalog = {}
    for path in sorted(SONGS_DIR.rglob("*.md")):
        key = path.relative_to(ROOT).as_posix()
        title = path.stem.replace("_", " ").replace("-", " ").title()
        catalog[key] = (title, path)
    return catalog


def create_presentation(songs: list[tuple[str, Path]]) -> tuple[bytes, int]:
    with tempfile.TemporaryDirectory(prefix="cantus-") as directory:
        temp_dir = Path(directory)
        index_path = temp_dir / "index.md"
        rows = [
            "| Ordre | Moment | Titre | Fichier |",
            "| --- | --- | --- | --- |",
        ]
        for position, (title, path) in enumerate(songs, start=1):
            relative_path = os.path.relpath(path, temp_dir).replace(os.sep, "/")
            link = quote(relative_path, safe="/.")
            rows.append(f"| {position} | Chant | {title.replace('|', ' ')} | [Paroles]({link}) |")
        index_path.write_text("\n".join(rows), encoding="utf-8")

        output_path = temp_dir / "diaporama.pptx"
        slide_count = convert(index_path, output_path, from_index=True)
        return output_path.read_bytes(), slide_count


def download_name(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", normalized).strip("_").lower()
    return f"{slug or 'messe'}.pptx"


def main() -> None:
    st.set_page_config(page_title="Préparer les chants", page_icon="🎵")
    st.title("Préparer un diaporama de chants")

    catalog = song_catalog()
    if not catalog:
        st.error("Aucun chant n’a été trouvé dans le catalogue.")
        return

    st.session_state.setdefault("song_order", [])
    celebration = st.text_input("Nom de la célébration", value="Messe")
    selected = st.selectbox(
        "Choisir un chant à ajouter",
        options=list(catalog),
        format_func=lambda key: catalog[key][0],
    )
    if st.button("Ajouter le chant"):
        st.session_state.song_order.append(selected)
        st.rerun()

    st.subheader("Ordre des chants")
    song_order = st.session_state.song_order
    if not song_order:
        st.info("Ajoutez un chant pour commencer.")
    else:
        for position, key in enumerate(song_order):
            title_col, up_col, down_col, remove_col = st.columns([6, 1, 1, 1])
            title_col.write(f"{position + 1}. {catalog[key][0]}")
            if up_col.button("Monter", key=f"up-{position}", disabled=position == 0):
                song_order[position - 1], song_order[position] = song_order[position], song_order[position - 1]
                st.rerun()
            if down_col.button(
                "Descendre",
                key=f"down-{position}",
                disabled=position == len(song_order) - 1,
            ):
                song_order[position + 1], song_order[position] = song_order[position], song_order[position + 1]
                st.rerun()
            if remove_col.button("Retirer", key=f"remove-{position}"):
                song_order.pop(position)
                st.rerun()

        with st.expander("Aperçu des paroles"):
            for position, key in enumerate(song_order, start=1):
                title, path = catalog[key]
                st.markdown(f"**{position}. {title}**")
                st.text("\n\n---\n\n".join(read_slides(path)))

    signature = (celebration.strip(), tuple(song_order))
    generated = st.session_state.get("generated_presentation")
    if st.button("Créer le PowerPoint", type="primary", disabled=not song_order):
        try:
            data, slide_count = create_presentation([catalog[key] for key in song_order])
            generated = (signature, data, slide_count)
            st.session_state.generated_presentation = generated
        except (OSError, ValueError) as error:
            st.error(f"La création a échoué : {error}")

    generated = st.session_state.get("generated_presentation")
    if generated and generated[0] == signature:
        st.download_button(
            "Télécharger le PowerPoint",
            data=generated[1],
            file_name=download_name(celebration),
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            type="primary",
        )
        st.caption(f"{generated[2]} diapositives")


if __name__ == "__main__":
    main()