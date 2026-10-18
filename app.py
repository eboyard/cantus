"""Interface Streamlit pour preparer un diaporama de chants."""

from __future__ import annotations

import os
import hmac
from datetime import datetime
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import quote
from zoneinfo import ZoneInfo

import streamlit as st

from scripts.markdown_to_pptx import convert, read_slides, read_title
from scripts.song_sheet import create_song_sheet
from scripts.print_song_sheet import create_print_song_sheet
from scripts.github_pages import prepare_pages_export, save_pages_export
from scripts.github_publish import publish_sheet


ROOT = Path(__file__).resolve().parent
SONGS_DIR = ROOT / "chants"


def song_catalog() -> dict[str, tuple[str, Path]]:
    catalog = {}
    for path in sorted(SONGS_DIR.rglob("*.md")):
        key = path.relative_to(ROOT).as_posix()
        title = read_title(path)
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


def github_setting(name: str, default: str = "") -> str:
    environment = {"token": "GITHUB_TOKEN", "repository": "GITHUB_REPOSITORY", "branch": "GITHUB_BRANCH", "publish_password": "SHEET_PUBLISH_PASSWORD"}
    if value := os.environ.get(environment[name]):
        return value
    try:
        return str(st.secrets["github"].get(name, default))
    except (FileNotFoundError, KeyError):
        return default


def show_github_pages(signature: tuple, celebration: str, songs: list[tuple[str, Path]]) -> None:
    st.markdown("**Partager avec GitHub Pages**")
    parish = st.selectbox(
        "Paroisse",
        options=["Boussy-saint-Antoine", "Quincy-sous-Sénart"],
        key="pages_parish",
    )
    day = st.date_input("Date de la célébration", value=datetime.now(ZoneInfo("Europe/Paris")).date())
    base_url = st.text_input(
        "Adresse du site GitHub Pages",
        value=os.environ.get("GITHUB_PAGES_URL", "https://eboyard.github.io/cantus/"),
    )
    export_signature = (signature, parish.strip(), day, base_url.strip())
    if st.button("Préparer pour GitHub Pages"):
        try:
            heading = f"{parish.strip()} — {celebration.strip() or 'Messe'} — {day.strftime('%d/%m/%Y')}"
            document = create_song_sheet(heading, songs)
            export = prepare_pages_export(document, parish, day, base_url)
            st.session_state.pages_export = (export_signature, export)
        except (OSError, ValueError) as error:
            st.error(f"La préparation a échoué : {error}")
    prepared = st.session_state.get("pages_export")
    if not prepared or prepared[0] != export_signature:
        return
    export = prepared[1]
    token = github_setting("token")
    password = github_setting("publish_password")
    repository = github_setting("repository", "eboyard/cantus")
    branch = github_setting("branch", "main")
    replace = st.checkbox("Remplacer la feuille existante pour cette paroisse et cette date")
    if not token or not password:
        st.info("Pour activer la publication directe, configurez le jeton GitHub et le code de publication dans les secrets Streamlit (voir README).")
    publication_code = st.text_input("Code de publication", type="password", key="pages_publish_password")
    if st.button("Publier sur GitHub Pages", type="primary", disabled=not token or not password):
        try:
            if not hmac.compare_digest(publication_code.encode("utf-8"), password.encode("utf-8")):
                raise ValueError("Le code de publication est incorrect.")
            with st.spinner("Envoi de la feuille sur GitHub…"):
                commit_url = publish_sheet(export, token, repository=repository, branch=branch, replace=replace)
            st.session_state.pages_publication = (export_signature, repository, branch, commit_url)
        except ValueError as error:
            st.error(str(error))
    publication = st.session_state.get("pages_publication")
    if publication and publication[:3] == (export_signature, repository, branch):
        st.success("La feuille a été envoyée sur GitHub. Elle sera accessible après le déploiement GitHub Pages.")
        st.link_button("Voir le commit publié", publication[3])
        st.link_button("Ouvrir la feuille après déploiement", export.url)
        st.link_button("Toutes les feuilles de la paroisse", export.parish_url)
    st.caption("Lien prévu : il sera accessible après l'envoi des fichiers sur GitHub et le déploiement Pages.")
    st.code(export.url, language=None)
    st.image(export.qr.decode("utf-8"), caption="QR code à distribuer après publication", width=280)
    st.download_button(
        "Télécharger les fichiers pour GitHub Pages (.zip)", export.archive,
        file_name=f"publication_{export.path.replace('/', '_')}.zip", mime="application/zip",
    )
    st.download_button(
        "Télécharger le QR code à imprimer (.svg)", export.qr,
        file_name=f"qr_{export.path.replace('/', '_')}.svg", mime="image/svg+xml",
    )
    with st.expander("Enregistrer les fichiers dans ce dépôt local"):
        if st.button("Enregistrer dans docs/"):
            try:
                target = save_pages_export(export, ROOT / "docs", replace=replace)
                st.success(f"Fichiers enregistrés : {target.relative_to(ROOT).as_posix()}")
            except (OSError, ValueError) as error:
                st.error(str(error))
    st.markdown(
        "Vous pouvez aussi décompresser le ZIP à la racine de votre copie du dépôt "
        "(ou utiliser l'enregistrement local ci-dessus), puis envoyer les fichiers sur GitHub. "
        "Conservez les anciennes feuilles pour garder leurs liens actifs."
    )
    st.caption(
        "Configuration GitHub Pages : Settings → Pages → Deploy from a branch → main → /docs. "
        "Si Streamlit est hébergé en ligne, téléchargez le ZIP pour récupérer les fichiers sur votre ordinateur."
    )


def main() -> None:
    st.set_page_config(page_title="Préparer les chants", page_icon="🎵")
    st.title("Préparer les chants de la célébration")

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
                try:
                    st.text("\n\n---\n\n".join(read_slides(path)))
                except (OSError, ValueError) as error:
                    st.error(f"Impossible de lire {path.name} : {error}")

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

    st.subheader("Feuille de chants à imprimer")
    st.caption("PDF A4 en deux colonnes, en noir et blanc. Chaque refrain est écrit une fois par chant.")
    print_size = st.selectbox("Taille du texte imprimé", options=[11, 12], format_func=lambda size: f"{size} points")
    print_signature = (signature, print_size)
    if st.button("Créer la version à imprimer", disabled=not song_order):
        try:
            pdf, pages = create_print_song_sheet(celebration, [catalog[key] for key in song_order], font_size=print_size)
            st.session_state.generated_print_sheet = (print_signature, pdf, pages)
        except (OSError, ValueError) as error:
            st.error(f"La création du PDF a échoué : {error}")
    printed = st.session_state.get("generated_print_sheet")
    if printed and printed[0] == print_signature:
        st.download_button(
            "Télécharger la version à imprimer (.pdf)", data=printed[1],
            file_name="feuille_" + Path(download_name(celebration)).with_suffix(".pdf").name,
            mime="application/pdf",
        )
        st.caption(f"{printed[2]} page(s) A4 — Imprimer à taille réelle (100 %), en recto verso, retournement sur le bord long.")

    st.subheader("Feuille de chants pour téléphone")
    st.caption("Un fichier HTML avec un sommaire et des paroles adaptées à la largeur de l'écran.")
    if st.button("Créer la feuille de chants", disabled=not song_order):
        try:
            data = create_song_sheet(celebration, [catalog[key] for key in song_order])
            st.session_state.generated_song_sheet = (signature, data)
        except (OSError, ValueError) as error:
            st.error(f"La création de la feuille a échoué : {error}")

    sheet = st.session_state.get("generated_song_sheet")
    if sheet and sheet[0] == signature:
        st.download_button(
            "Télécharger la feuille de chants (.html)",
            data=sheet[1],
            file_name="feuille_" + Path(download_name(celebration)).with_suffix(".html").name,
            mime="text/html",
        )
        st.caption(
            "Transférez le fichier sur le téléphone et ouvrez-le avec un navigateur. "
            "Une fois enregistré, il se lit sans connexion Internet."
        )
        show_github_pages(signature, celebration, [catalog[key] for key in song_order])


if __name__ == "__main__":
    main()
