"""Interface Streamlit pour preparer un diaporama de chants."""

from __future__ import annotations

import os
import hmac
import logging
from datetime import date, datetime
from pathlib import Path
import re
import tempfile
import unicodedata
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components

from scripts.markdown_to_pptx import build_slides, plain_text, read_slides, read_title, write_slides
from scripts.song_sheet import create_song_sheet
from scripts.song_selection import selected_song_parts, with_liturgical_introductions
from scripts.word_song_sheet import create_word_song_sheet, DEFAULT_PLACE, MIME as WORD_MIME
from scripts.github_pages import prepare_pages_export
from scripts.github_publish import publish_sheet
from scripts.song_editor import SongDraft, create_song, load_song, new_song_path, save_song, serialize_song
from scripts.song_types import MOMENTS, celebration_moments, moment_insertion_index, read_song_type, song_type, set_song_type
from scripts.lyrics_format import lyrics_html
from scripts.sheet_library import local_sheets, published_sheets, read_existing_sheet, songs_from_contents, verses_from_contents, title_from_contents
from scripts.sheet_library import aelf_psalms_from_contents, aelf_context_from_contents, moments_from_contents
from scripts.aelf import load_aelf_masses, mass_url, psalm_catalog, preferred_psalm_key
from scripts.psautier import INDEX as PSAUTIER_INDEX, PSALM_REFERENCE, import_psalm, reference_label
from scripts.liturgical_texts import reading_catalog, reading_documents
from scripts.sheet_library import reading_texts_from_contents


ROOT = Path(__file__).resolve().parent
SONGS_DIR = ROOT / "chants"
USER_HELP_PATH = ROOT / "help" / "guide_utilisateur.md"


def song_catalog() -> dict[str, tuple[str, Path]]:
    catalog = {}
    for path in sorted(SONGS_DIR.rglob("*.md")):
        key = path.relative_to(ROOT).as_posix()
        title = read_title(path)
        catalog[key] = (title, path)
    return catalog


def create_presentation(
    songs: list[tuple[str, Path]], *, verses: list[list[str] | None] | None = None,
    moments: list[str] | None = None,
    aelf_context: str | None = None,
) -> tuple[bytes, int]:
    if verses is not None and len(verses) != len(songs):
        raise ValueError("Choisissez les couplets pour chaque chant.")
    sections = []
    if moments is None:
        moments = [read_song_type(path) for _, path in songs]
    if len(moments) != len(songs):
        raise ValueError("Choisissez une rubrique pour chaque chant.")
    for position, (_, path) in enumerate(songs):
        parts = selected_song_parts(path, None if verses is None else verses[position])
        parts = with_liturgical_introductions(parts, moments[position], moments=moments)
        if not parts:
            raise ValueError(f"Le chant {path.name} ne contient aucune parole après sélection.")
        if sections:
            sections.append("")
        sections.extend(part.text for part in parts)
    with tempfile.TemporaryDirectory(prefix="cantus-") as directory:
        output_path = Path(directory) / "diaporama.pptx"
        slide_count = write_slides(sections, output_path)
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


def show_github_pages(
    signature: tuple, celebration: str, songs: list[tuple[str, Path]], day: date, moments: list[str],
    verses: list[list[str] | None],
    *, aelf_context: str | None = None,
) -> None:
    st.markdown("**Partager avec GitHub Pages**")
    parish = st.selectbox(
        "Paroisse",
        options=["Boussy-saint-Antoine", "Quincy-sous-Sénart"],
        key="pages_parish",
    )
    base_url = st.text_input(
        "Adresse du site GitHub Pages",
        value=os.environ.get("GITHUB_PAGES_URL", "https://eboyard.github.io/cantus/"),
    )
    export_signature = (signature, parish.strip(), day, base_url.strip())
    if st.button("Préparer pour GitHub Pages"):
        try:
            heading = f"{parish.strip()} — {celebration.strip() or 'Messe'}"
            document = create_song_sheet(heading, songs, day=day, moments=moments, verses=verses,
                                         celebration_title=celebration, aelf_context=aelf_context)
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
        st.link_button("Ouvrir la feuille après déploiement", export.url)
        st.link_button("Toutes les feuilles de la paroisse", export.parish_url)
    st.caption("Lien prévu : il sera accessible après l'envoi des fichiers sur GitHub et le déploiement Pages.")
    st.code(export.url, language=None)
    st.image(export.qr.decode("utf-8"), caption="QR code à distribuer après publication", width=280)
    st.download_button(
        "Télécharger le QR code à imprimer (.svg)", export.qr,
        file_name=f"qr_{export.path.replace('/', '_')}.svg", mime="image/svg+xml",
    )


def show_existing_sheets(catalog: dict[str, tuple[str, Path]]) -> None:
    with st.expander("Repartir d’une feuille existante"):
        st.caption("Choisissez une feuille : ses chants remplaceront la liste actuelle, dans le même ordre, avec les couplets mémorisés lors de la publication.")
        repository = github_setting("repository", "eboyard/cantus")
        branch = github_setting("branch", "main")
        source_signature = (repository, branch)
        choice_column, refresh_column = st.columns([8, 1], vertical_alignment="bottom")
        if refresh_column.button("↻", key="refresh_existing_sheets", help="Actualiser les feuilles depuis GitHub"):
            try:
                with st.spinner("Recherche des feuilles publiées…"):
                    sheets = published_sheets(github_setting("token"), repository, branch)
                st.session_state.existing_remote_sheets = (source_signature, sheets)
                st.session_state.existing_sheet_choice = None
                st.session_state.pop("sheet_import_status", None)
            except ValueError as error:
                st.error(str(error))
        remote = st.session_state.get("existing_remote_sheets")
        sheets = remote[1] if remote and remote[0] == source_signature else local_sheets(ROOT / "docs")
        choices = {sheet.path: sheet for sheet in sheets}

        def import_sheet():
            chosen = st.session_state.existing_sheet_choice
            if chosen is None:
                return
            try:
                document = read_existing_sheet(choices[chosen], ROOT / "docs", github_setting("token"), repository)
                aelf_documents = {**st.session_state.get("aelf_psalms", {}), **aelf_psalms_from_contents(document)}
                imported_catalog = {**catalog, **psalm_catalog(aelf_documents, ROOT)}
                readings = {**st.session_state.get("reading_texts", {}), **reading_texts_from_contents(document)}
                imported_catalog.update(reading_catalog(readings, ROOT))
                order = songs_from_contents(document, imported_catalog)
                verses = verses_from_contents(document, order, imported_catalog)
                moments = moments_from_contents(document, order, imported_catalog)
                title = title_from_contents(document)
                context = aelf_context_from_contents(document)
                catalog.update(imported_catalog)
                st.session_state.aelf_psalms = aelf_documents
                st.session_state.reading_texts = readings
                st.session_state.selected_aelf_context = context
                st.session_state.song_order = order
                st.session_state.song_moments = moments
                st.session_state.song_verses = verses
                st.session_state.pop("selected_daily_psalm", None)
                if title is not None:
                    st.session_state.celebration_title = title
                clear_moment_widgets()
                for key in ("generated_song_sheet", "generated_print_sheet", "generated_presentation", "pages_export", "pages_publication"):
                    st.session_state.pop(key, None)
                st.session_state.sheet_import_status = (True, f"{len(order)} chant(s) chargés. Vous pouvez modifier cette liste pour préparer la nouvelle feuille.")
            except (OSError, ValueError) as error:
                st.session_state.sheet_import_status = (False, str(error))

        choice_column.selectbox(
            "Choisir une feuille de chants existante", options=list(choices),
            format_func=lambda path: choices[path].label, index=None,
            placeholder="Choisir une feuille", key="existing_sheet_choice", on_change=import_sheet,
        )
        if not sheets:
            st.info("Aucune feuille disponible. Actualisez depuis GitHub pour rechercher les feuilles publiées.")
        if not remote or remote[0] != source_signature:
            st.caption("Les feuilles de cette copie du projet sont proposées. Actualisez depuis GitHub pour récupérer les dernières publications.")
        status = st.session_state.get("sheet_import_status")
        if status:
            (st.success if status[0] else st.error)(status[1])


def show_song_editor(selected: str, path: Path, title: str) -> bool:
    """Charge la version distante, conserve le brouillon et protège les écritures."""
    token = github_setting("token")
    password = github_setting("publish_password")
    repository = github_setting("repository", "eboyard/cantus")
    branch = github_setting("branch", "main")
    signature = (selected, repository, branch)
    editor = st.session_state.get("song_editor")
    if editor and editor[0] != signature:
        st.session_state.pop("song_editor", None)
        editor = None
    if not editor:
        if st.button("Modifier", disabled=not token or not password):
            try:
                with st.spinner("Chargement du chant depuis GitHub…"):
                    document, sha = load_song(token, repository, branch, selected)
                st.session_state.song_editor = (signature, document, sha)
                st.session_state.pop("song_edit_result", None)
                # Un nouveau formulaire ne récupère jamais les champs d'un autre chant.
                for key in list(st.session_state):
                    if key.startswith("song_edit_"):
                        del st.session_state[key]
                st.rerun()
            except ValueError as error:
                st.error(str(error))
        if not token or not password:
            st.caption("L’édition sera disponible après configuration de l’accès GitHub et du code de publication.")
        return False

    with st.form("song_editor_form"):
        document = st.text_area("Contenu Markdown", value=editor[1], height=500, key="song_edit_markdown")
        initial_type = song_type(editor[1])
        selected_type = st.selectbox(
            "Type du chant dans le carnet", options=["", *MOMENTS],
            index=["", *MOMENTS].index(initial_type), key="song_edit_type",
            format_func=lambda value: value or "Non renseigné",
        )
        publication_code = st.text_input("Code de publication", type="password", key="song_edit_password")
        submitted = st.form_submit_button("Enregistrer", type="primary", disabled=not token or not password)
        cancelled = st.form_submit_button("Annuler")
    if cancelled:
        st.session_state.pop("song_editor", None)
        st.rerun()
    if submitted:
        try:
            check_song_publication_code(publication_code, password, token)
            if selected_type != initial_type:
                document = set_song_type(document, selected_type)
            if document == editor[1]:
                st.info("Aucune modification à enregistrer.")
                return True
            if not document.strip() or not any(part.strip() for part in build_slides(document)):
                raise ValueError("Le chant ne peut pas être vide.")
            with st.spinner("Enregistrement sur GitHub…"):
                commit_url = save_song(token, repository, branch, selected, document, editor[2])
        except ValueError as error:
            st.error(str(error))
            return True
        # L'écriture locale n'a lieu qu'après confirmation de GitHub.
        warning = ""
        try:
            path.write_text(document, encoding="utf-8")
        except OSError:
            warning = "Le chant est enregistré sur GitHub, mais la copie locale n’a pas pu être actualisée. Rechargez le déploiement pour le consulter."
        for key in ("song_editor", "generated_song_sheet", "generated_print_sheet", "generated_presentation", "pages_export", "pages_publication"):
            st.session_state.pop(key, None)
        st.session_state.song_edit_result = (selected, commit_url, warning)
        st.rerun()
    return True


def check_song_publication_code(code: str, password: str, token: str) -> None:
    if not token or not password:
        raise ValueError("Configurez l’accès GitHub et le code de publication pour enregistrer un chant.")
    if not hmac.compare_digest(code.encode("utf-8"), password.encode("utf-8")):
        raise ValueError("Le code de publication est incorrect.")


def show_song_creator() -> bool:
    token = github_setting("token")
    password = github_setting("publish_password")
    repository = github_setting("repository", "eboyard/cantus")
    branch = github_setting("branch", "main")
    signature = (repository, branch)
    if st.session_state.get("song_creator") != signature:
        st.session_state.pop("song_creator", None)
    if "song_creator" not in st.session_state:
        if st.button("Ajouter un chant", type="primary", disabled=not token or not password):
            for key in list(st.session_state):
                if key.startswith("song_create_"):
                    del st.session_state[key]
            st.session_state.pop("song_editor", None)
            st.session_state.song_creator = signature
            st.rerun()
        if not token or not password:
            st.caption("L’ajout sera disponible après configuration de l’accès GitHub et du code de publication.")
        return False

    st.subheader("Ajouter un chant")
    with st.form("song_creator_form"):
        title = st.text_input("Titre du chant", key="song_create_title")
        lyrics = st.text_area("Paroles (Markdown)", height=400, key="song_create_lyrics",
                              help="Séparez les parties par --- ; utilisez <!-- refrain --> et <!-- couplet --> pour les identifier.")
        selected_type = st.selectbox(
            "Type du chant dans le carnet", options=["", *MOMENTS], key="song_create_type",
            format_func=lambda value: value or "Non renseigné",
        )
        publication_code = st.text_input("Code de publication", type="password", key="song_create_password")
        submitted = st.form_submit_button("Enregistrer", type="primary", disabled=not token or not password)
        cancelled = st.form_submit_button("Annuler")
    if cancelled:
        st.session_state.pop("song_creator", None)
        st.rerun()
    if submitted:
        try:
            check_song_publication_code(publication_code, password, token)
            document = set_song_type(serialize_song(SongDraft(title, lyrics)), selected_type)
            selected = new_song_path(title)
            path = ROOT / selected
            if path.exists():
                raise ValueError("Un chant utilise déjà ce nom de fichier. Choisissez un titre distinct, par exemple en ajoutant l’auteur ou la messe.")
            with st.spinner("Enregistrement sur GitHub…"):
                commit_url = create_song(token, repository, branch, selected, document)
        except ValueError as error:
            st.error(str(error))
            return True
        warning = ""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as output:
                output.write(document)
        except OSError:
            warning = "Le chant est enregistré sur GitHub, mais la copie locale n’a pas pu être actualisée. Rechargez le déploiement pour le consulter."
        st.session_state.pop("song_creator", None)
        st.session_state.song_create_result = (commit_url, warning)
        if not warning:
            st.session_state.lyrics_song = selected
        st.rerun()
    return True


def show_lyrics() -> None:
    st.title("carnet de chants")
    st.caption("Choisissez un chant du catalogue pour vérifier ses paroles avant de préparer la célébration.")
    result = st.session_state.get("song_create_result")
    if result:
        st.success("Le nouveau chant a été enregistré sur GitHub.")
        st.link_button("Voir l’ajout", result[0])
        if result[1]:
            st.warning(result[1])
    if show_song_creator():
        return
    catalog = song_catalog()
    if not catalog:
        st.info("Aucun chant n’a été trouvé dans le catalogue.")
        return

    selected = st.selectbox(
        "Choisir un chant à consulter",
        options=sorted(catalog, key=lambda key: (catalog[key][0].casefold(), key)),
        format_func=lambda key: catalog[key][0],
        index=None,
        placeholder="Rechercher un chant par son titre",
        key="lyrics_song",
    )
    if selected is None:
        return

    title, path = catalog[selected]
    st.subheader(title)
    result = st.session_state.get("song_edit_result")
    if result and result[0] == selected:
        st.success("Le chant a été enregistré sur GitHub.")
        st.link_button("Voir la modification", result[1])
        if result[2]:
            st.warning(result[2])
    if show_song_editor(selected, path, title):
        return
    try:
        st.caption(f"Type du chant : {read_song_type(path) or 'Non renseigné'}")
        slides = read_slides(path)
    except (OSError, ValueError) as error:
        st.error(f"Impossible de lire les paroles de {title} : {error}")
        return
    if not slides:
        st.info("Ce chant ne contient aucune parole.")
        return

    st.caption("Les parties sont présentées dans l’ordre de projection, avec les reprises du refrain.")
    for position, text in enumerate(slides):
        if position:
            st.divider()
        if re.search(r"</?u>", text, re.IGNORECASE):
            st.markdown(lyrics_html(text), unsafe_allow_html=True)
        else:
            st.markdown(text.replace("\n", "  \n"))


def show_published_sheets() -> None:
    st.title("Feuilles de chants publiées")
    st.caption("Retrouvez les feuilles de chants par paroisse et par date.")
    url = os.environ.get("GITHUB_PAGES_URL", "https://eboyard.github.io/cantus/")
    st.link_button("Ouvrir le site dans un nouvel onglet", url)
    if hasattr(st, "iframe"):
        st.iframe(url, height=800, alt="Feuilles de chants publiées")
    else:
        components.iframe(url, height=800, scrolling=True)


def show_user_help() -> None:
    st.title("Aide Cantus")
    st.caption("Retrouvez les étapes pour préparer et partager les chants de votre célébration.")
    document = USER_HELP_PATH.read_text(encoding="utf-8")
    _, *sections = document.split("\n## ")
    topics = {section.split("\n", 1)[0]: "## " + section for section in sections}
    topic = st.selectbox("Consulter une rubrique", ["Toutes les rubriques", *topics], key="user_help_topic")
    st.markdown(document if topic == "Toutes les rubriques" else topics[topic])


def clear_moment_widgets() -> None:
    for key in list(st.session_state):
        if key.startswith(("sheet_moment_", "sheet_verses_")):
            del st.session_state[key]


def show_aelf_import(catalog: dict[str, tuple[str, Path]]) -> date:
    """Charge à la demande ou lors du changement de date ; ne requiert pas de réseau au démarrage."""
    def apply_choice():
        _, masses = st.session_state.aelf_loaded
        chosen = next(mass for mass in masses if mass.key == st.session_state.aelf_mass_choice)
        reference = PSALM_REFERENCE.match(chosen.reference)
        psautier_key = reference[1].lower() if reference else None
        st.session_state.psautier_choice = psautier_key if psautier_key in PSAUTIER_INDEX else None
        st.session_state.selected_aelf_context = chosen.markdown or None
        st.session_state.celebration_title = chosen.title
        preferred_key = preferred_psalm_key(chosen, catalog)
        previous_key = st.session_state.get("selected_daily_psalm")
        # Un psaume déjà importé suit la nouvelle date ou la nouvelle messe choisie.
        for position, key in enumerate(st.session_state.song_order):
            if chosen.markdown and (key.startswith("aelf/") or key == previous_key):
                if key != preferred_key:
                    st.session_state.song_order[position] = preferred_key
                    st.session_state.song_verses[position] = None
                    st.session_state.song_moments[position] = "Psaume"
                st.session_state.selected_daily_psalm = preferred_key
        for key in ("generated_song_sheet", "generated_print_sheet", "generated_presentation", "pages_export", "pages_publication"):
            st.session_state.pop(key, None)
        clear_moment_widgets()

    def retrieve():
        day = st.session_state.celebration_date
        try:
            with st.spinner("Récupération du nom de la messe et du psaume sur AELF…"):
                masses = load_aelf_masses(day)
                documents = {**st.session_state.get("aelf_psalms", {}),
                             **{mass.key: mass.markdown for mass in masses if mass.markdown}}
                additions = psalm_catalog(documents, ROOT)
            catalog.update(additions)
            st.session_state.aelf_psalms = documents
            st.session_state.aelf_loaded = (day, masses)
            st.session_state.aelf_mass_choice = masses[0].key
            st.session_state.pop("aelf_import_error", None)
            apply_choice()
        except (OSError, ValueError) as error:
            st.session_state.aelf_import_error = (day, str(error))

    date_column, consult_column = st.columns([2, 3], vertical_alignment="bottom")
    with date_column:
        day = st.date_input(
            "Date de la célébration", value=datetime.now(ZoneInfo("Europe/Paris")).date(),
            key="celebration_date", on_change=retrieve,
        )
    with consult_column:
        st.link_button("Consulter la messe du jour sur AELF", mass_url(day))
    st.session_state.setdefault("celebration_title", "Messe")
    st.text_input("Nom de la célébration", key="celebration_title")
    st.caption("Changer la date récupère automatiquement les textes AELF du jour exact choisi. Le titre reste modifiable.")
    status = st.session_state.get("aelf_import_error")
    if status and status[0] == day:
        st.error(status[1] + " Le nom et les chants en cours ont été conservés.")
    loaded = st.session_state.get("aelf_loaded")
    if loaded and loaded[0] == day:
        masses = loaded[1]
        if len(masses) > 1:
            options = {mass.key: mass for mass in masses}
            st.selectbox("Messe et psaume proposés par l’AELF", list(options), key="aelf_mass_choice",
                         format_func=lambda key: f"{options[key].name} — {options[key].reference or 'Sans psaume ni cantique'}",
                         on_change=apply_choice)
        chosen = next(mass for mass in masses if mass.key == st.session_state.aelf_mass_choice)
        if not chosen.markdown:
            st.info("Le nom de la célébration a été récupéré. Aucun psaume ni cantique n’est proposé par l’AELF ; les chants choisis ont été conservés.")
    return day


def show_preparation() -> None:
    st.title("Préparer les chants de la célébration")

    catalog = song_catalog()
    catalog.update(psalm_catalog(st.session_state.get("aelf_psalms", {}), ROOT))
    catalog.update(reading_catalog(st.session_state.get("reading_texts", {}), ROOT))
    if not catalog:
        st.error("Aucun chant n’a été trouvé dans le catalogue.")
        return

    st.session_state.setdefault("song_order", [])
    show_existing_sheets(catalog)
    if ("song_moments" not in st.session_state
            or len(st.session_state.song_moments) != len(st.session_state.song_order)):
        st.session_state.song_moments = celebration_moments([read_song_type(catalog[key][1]) for key in st.session_state.song_order])
        clear_moment_widgets()
    if ("song_verses" not in st.session_state
            or len(st.session_state.song_verses) != len(st.session_state.song_order)):
        st.session_state.song_verses = [None for _ in st.session_state.song_order]
        clear_moment_widgets()
    day = show_aelf_import(catalog)
    aelf_context = st.session_state.get("selected_aelf_context")
    celebration = st.session_state.celebration_title
    selected = st.selectbox(
        "Choisir un chant à ajouter",
        options=sorted((key for key in catalog if not key.startswith("reading/")),
                       key=lambda key: (catalog[key][0].casefold(), key)),
        format_func=lambda key: catalog[key][0],
    )
    if st.button("Ajouter le chant"):
        moment = read_song_type(catalog[selected][1]) or (MOMENTS[0] if not st.session_state.song_order else "")
        position = moment_insertion_index(st.session_state.song_moments, moment)
        st.session_state.song_order.insert(position, selected)
        st.session_state.song_moments.insert(position, moment)
        st.session_state.song_verses.insert(position, None)
        clear_moment_widgets()
        st.rerun()

    psautier_choice = st.selectbox(
        "Choisir un psaume ou cantique à ajouter", options=list(PSAUTIER_INDEX),
        index=None, placeholder="Psaumes et cantiques de Psautier.org",
        format_func=reference_label, key="psautier_choice",
    )
    add_psautier_column, psautier_link_column = st.columns(2)
    psautier_link_column.link_button("Consulter Psautier.org", "https://psautier.org/")
    if add_psautier_column.button("Ajouter le psaume ou cantique", key="add_psautier",
                                 disabled=psautier_choice is None) and psautier_choice is not None:
        try:
            with st.spinner("Récupération du psaume ou cantique sur Psautier.org…"):
                path = import_psalm(psautier_choice, ROOT / "chants")
            key = path.relative_to(ROOT).as_posix()
        except (OSError, ValueError, UnicodeError) as error:
            st.error(f"Impossible d’ajouter le psaume ou cantique : {error}")
        else:
            position = moment_insertion_index(st.session_state.song_moments, "Psaume")
            st.session_state.song_order.insert(position, key)
            st.session_state.song_moments.insert(position, "Psaume")
            st.session_state.song_verses.insert(position, None)
            clear_moment_widgets()
            st.rerun()

    if aelf_context:
        available_readings = reading_documents(aelf_context or "")
        reading_options = reading_catalog(available_readings, ROOT)
        if reading_options:
            st.markdown("**Ajouter un texte de lecture**")
            st.caption("Chaque bouton ajoute un intitulé à la fin de la liste. Déplacez-le ensuite à l’endroit souhaité.")
            reading_columns = st.columns(len(reading_options))
            for column, (reading_key, (title, _)) in zip(reading_columns, reading_options.items()):
                if column.button(f"Ajouter : {title}", key=f"add_{title}"):
                    st.session_state.reading_texts = {**st.session_state.get("reading_texts", {}),
                                                      reading_key: available_readings[reading_key]}
                    st.session_state.song_order.append(reading_key)
                    st.session_state.song_moments.append("")
                    st.session_state.song_verses.append(None)
                    clear_moment_widgets()
                    st.rerun()

    st.subheader("Ordre des chants et des textes")
    song_order = st.session_state.song_order
    assigned_moments = st.session_state.song_moments
    verses = st.session_state.song_verses
    moments = list(assigned_moments)
    if not song_order:
        st.info("Ajoutez un chant ou un texte pour commencer.")
    else:
        st.caption("Le type du carnet est proposé pour chaque chant. Vous pouvez modifier tous les moments, y compris le premier et le dernier. Les moments suivent les chants lorsque vous les déplacez et sont conservés dans les feuilles publiées.")
        for position, key in enumerate(song_order):
            title_col, up_col, down_col, remove_col = st.columns([6, 1, 1, 1])
            title_col.write(f"{position + 1}. {catalog[key][0]}")
            moments[position] = title_col.selectbox(
                f"Moment de la messe — {'texte' if key.startswith('reading/') else 'chant'} {position + 1}", options=["", *MOMENTS],
                index=["", *MOMENTS].index(moments[position]),
                key=f"sheet_moment_{position}",
                format_func=lambda value: f"{MOMENTS.index(value) + 1}. {value}" if value else "Non renseigné",
            )
            assigned_moments[position] = moments[position]
            try:
                parts = selected_song_parts(catalog[key][1])
                couplets = {part.identifier: part.text for part in parts if part.selectable}
                if len(couplets) <= 1:
                    verses[position] = list(couplets)
                else:
                    selected_verses = list(couplets) if verses[position] is None else [
                        identifier for identifier in verses[position] if identifier in couplets
                    ]
                    title_col.caption("Couplets à garder")
                    verses[position] = [
                        identifier for identifier, text in couplets.items()
                        if title_col.checkbox(
                            f"Couplet {identifier[1:]} — {plain_text(text).splitlines()[0]}",
                            value=identifier in selected_verses,
                            key=f"sheet_verses_{position}_{identifier}",
                            help="Choix pour le PowerPoint et les feuilles téléphone, à publier et à imprimer. Les refrains et les ponts sont conservés.",
                        )
                    ]
            except (OSError, ValueError) as error:
                title_col.error(f"Impossible de lire les couplets : {error}")
            if up_col.button("Monter", key=f"up-{position}", disabled=position == 0):
                song_order[position - 1], song_order[position] = song_order[position], song_order[position - 1]
                assigned_moments[position - 1], assigned_moments[position] = assigned_moments[position], assigned_moments[position - 1]
                verses[position - 1], verses[position] = verses[position], verses[position - 1]
                clear_moment_widgets()
                st.rerun()
            if down_col.button(
                "Descendre",
                key=f"down-{position}",
                disabled=position == len(song_order) - 1,
            ):
                song_order[position + 1], song_order[position] = song_order[position], song_order[position + 1]
                assigned_moments[position + 1], assigned_moments[position] = assigned_moments[position], assigned_moments[position + 1]
                verses[position + 1], verses[position] = verses[position], verses[position + 1]
                clear_moment_widgets()
                st.rerun()
            if remove_col.button("Retirer", key=f"remove-{position}"):
                song_order.pop(position)
                assigned_moments.pop(position)
                verses.pop(position)
                clear_moment_widgets()
                st.rerun()

        with st.expander("Aperçu des paroles"):
            for position, key in enumerate(song_order, start=1):
                title, path = catalog[key]
                try:
                    parts = selected_song_parts(path, verses[position - 1])
                    for part in parts:
                        if part.kind == "lecture" and part.identifier == "L1":
                            st.markdown(lyrics_html(part.text), unsafe_allow_html=True)
                    st.markdown(f"**{position}. {title}**")
                    for part in with_liturgical_introductions(parts, moments[position - 1], moments=moments):
                        if part.kind == "lecture" and part.identifier == "L1":
                            continue
                        st.markdown(lyrics_html(part.text), unsafe_allow_html=True)
                except (OSError, ValueError) as error:
                    st.error(f"Impossible de lire {path.name} : {error}")

    signature = (celebration.strip(), tuple(song_order), aelf_context)
    verse_signature = tuple(None if selection is None else tuple(selection) for selection in verses)
    presentation_signature = (signature, verse_signature, tuple(moments))
    generated = st.session_state.get("generated_presentation")
    if st.button("Créer le PowerPoint", type="primary", disabled=not song_order):
        try:
            data, slide_count = create_presentation([catalog[key] for key in song_order], verses=verses, moments=moments,
                                                    aelf_context=aelf_context)
            generated = (presentation_signature, data, slide_count)
            st.session_state.generated_presentation = generated
        except (OSError, ValueError) as error:
            st.error(f"La création a échoué : {error}")

    generated = st.session_state.get("generated_presentation")
    if generated and generated[0] == presentation_signature:
        st.download_button(
            "Télécharger le PowerPoint",
            data=generated[1],
            file_name=download_name(celebration),
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            type="primary",
        )
        st.caption(f"{generated[2]} diapositives")

    st.subheader("Feuille de chants pour téléphone")
    st.caption("Un fichier HTML avec les paroles adaptées à la largeur de l'écran.")
    sheet_signature = (signature, day, tuple(moments), verse_signature)
    if st.button("Créer la feuille de chants", disabled=not song_order):
        try:
            data = create_song_sheet(celebration, [catalog[key] for key in song_order], day=day, moments=moments, verses=verses,
                                     aelf_context=aelf_context)
            st.session_state.generated_song_sheet = (sheet_signature, data)
        except (OSError, ValueError) as error:
            st.error(f"La création de la feuille a échoué : {error}")

    sheet = st.session_state.get("generated_song_sheet")
    if sheet and sheet[0] == sheet_signature:
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
        show_github_pages(sheet_signature, celebration, [catalog[key] for key in song_order], day, moments, verses,
                          aelf_context=aelf_context)

    st.subheader("Feuille de chants à imprimer")
    st.caption("Document Word modifiable, selon le modèle de Saint Pierre–Boussy. Ouvrez-le dans Word pour ajuster la mise en page et l’imprimer.")
    word_place = st.text_input("Lieu de la célébration", value=DEFAULT_PLACE, key="word_place")
    print_size = st.selectbox("Taille du texte imprimé", options=[9, 10, 11, 12], index=3,
                              format_func=lambda size: f"{size} points")
    print_signature = ("word-v1", signature, day, word_place.strip(), print_size, tuple(moments), verse_signature)
    if st.button("Créer la version à imprimer", disabled=not song_order):
        try:
            document = create_word_song_sheet(
                celebration, [catalog[key] for key in song_order], day=day, place=word_place,
                font_size=print_size, moments=moments, verses=verses, aelf_context=aelf_context,
            )
            st.session_state.generated_print_sheet = (print_signature, document)
        except (OSError, ValueError) as error:
            st.error(f"La création du document Word a échoué : {error}")
        except TypeError:
            logging.getLogger(__name__).exception("Échec de la création du document Word")
            st.error("La création du document Word a échoué à cause d’une erreur interne. Le détail est disponible dans les journaux de l’application.")
    printed = st.session_state.get("generated_print_sheet")
    if printed and printed[0] == print_signature:
        st.download_button(
            "Télécharger la version à imprimer (.docx)", data=printed[1],
            file_name="feuille_" + Path(download_name(celebration)).with_suffix(".docx").name,
            mime=WORD_MIME,
        )
        st.caption("La pagination est calculée par Word à l’ouverture. Vérifiez l’aperçu avant impression, puis imprimez en recto verso sur le bord long.")



def main() -> None:
    st.set_page_config(page_title="Cantus — Préparer les chants", page_icon="🎵")
    preparation, lyrics_tab, published_tab, help_tab = st.tabs(
        ["Préparer la célébration", "carnet de chants", "Feuilles publiées", "Aide en ligne"]
    )
    with preparation:
        show_preparation()
    with lyrics_tab:
        show_lyrics()
    with published_tab:
        show_published_sheets()
    with help_tab:
        show_user_help()


if __name__ == "__main__":
    main()
