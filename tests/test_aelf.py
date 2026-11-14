from copy import deepcopy
from datetime import date
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import URLError

from streamlit.testing.v1 import AppTest

from scripts.aelf import api_url, html_paragraphs, load_aelf_masses, parse_aelf_response, psalm_catalog
from scripts.markdown_to_pptx import build_song_parts
from scripts.sheet_library import aelf_psalms_from_contents, aelf_context_from_contents, songs_from_contents, title_from_contents, verses_from_contents
from scripts.song_sheet import create_song_sheet
from scripts.song_selection import selected_song_parts


DAY = date(2026, 11, 15)
FIXTURE = Path(__file__).parent / "fixtures/aelf_2026_11_15.json"


def response():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class AelfTests(unittest.TestCase):
    def test_publication_keeps_reading_headers_with_manual_psalm_and_after_reopening(self):
        payload = response()
        before = "Lecture du livre des Proverbes"
        after = "Lecture de la première lettre de saint Paul apôtre aux Thessaloniciens"
        gospel = "Évangile de Jésus Christ selon saint Matthieu"
        psalm = payload["messes"][0]["lectures"][0]
        payload["messes"][0]["lectures"] = [
            {"type": "lecture_1", "intro_lue": before}, psalm,
            {"type": "lecture_2", "intro_lue": after},
            {"type": "evangile", "intro_lue": gospel},
        ]
        mass, = parse_aelf_response(payload, DAY)
        root = Path(__file__).resolve().parents[1]
        catalog = {f"chants/{name}": (title, root / "chants" / name) for title, name in (
            ("Entrée", "habiter_le_seuil_de_ta_maison_seigneur.md"),
            ("Psaume 127", "psaume_127.md"),
            ("Alléluia (Messe de St Augustin)", "alleluia_messe_de_st_augustin.md"),
            ("Envoi", "je_veux_chanter_ton amour_seigneur.md"),
        )}
        psalm_path = catalog["chants/psaume_127.md"][1]
        original = psalm_path.read_text(encoding="utf-8")
        with TemporaryDirectory() as directory, patch("app.ROOT", Path(directory)), \
                patch("app.song_catalog", side_effect=lambda: dict(catalog)), \
                patch("app.load_aelf_masses", return_value=[mass]):
            app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20)
            app.session_state["song_order"] = list(catalog)
            app.session_state["celebration_date"] = DAY
            app.run()
            app.button(key="retrieve_aelf").click().run()
            # Garde le psaume du carnet : aucun clic sur « Utiliser le psaume du jour ».
            self.assertEqual(app.session_state["song_order"], list(catalog))
            next(b for b in app.button if b.label == "Créer la feuille de chants").click().run()
            next(b for b in app.button if b.label == "Préparer pour GitHub Pages").click().run()
            self.assertFalse(app.exception)
            published = app.session_state["pages_export"][1].document.decode()
            self.assertEqual(aelf_context_from_contents(published), mass.markdown)
            for text in (before, after, gospel):
                self.assertEqual(published.count(f"<strong>{text}</strong>"), 1)
            self.assertIn("<u>", published)
            source = Path(directory) / "docs/paroisse/2026-11-15/index.html"
            source.parent.mkdir(parents=True)
            source.write_text(published, encoding="utf-8")
            reopened = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20).run()
            reopened.selectbox(key="existing_sheet_choice").select("paroisse/2026-11-15/index.html").run()
            self.assertFalse(reopened.exception)
            self.assertEqual(reopened.session_state["selected_aelf_context"], mass.markdown)
            next(b for b in reopened.button if b.label == "Créer la feuille de chants").click().run()
            regenerated = reopened.session_state["generated_song_sheet"][1].decode()
            for text in (before, after, gospel):
                self.assertEqual(regenerated.count(f"<strong>{text}</strong>"), 1)
        self.assertEqual(psalm_path.read_text(encoding="utf-8"), original)

    def test_gospel_introduction_follows_alleluia_in_exports_and_after_reopening(self):
        import pymupdf
        from pptx import Presentation
        from app import create_presentation
        from scripts.print_song_sheet import create_print_song_sheet

        payload = response()
        intro = "Évangile de Jésus Christ selon saint Matthieu"
        payload["messes"][0]["lectures"].extend([
            {"type": "lecture_2", "intro_lue": "Lecture de la lettre de saint Paul"},
            {"type": "evangile", "intro_lue": f"<p>{intro}</p>"},
            {"type": "evangile", "intro_lue": intro},  # Forme brève : pas de doublon.
        ])
        mass, = parse_aelf_response(payload, DAY)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = psalm_catalog({mass.key: mass.markdown}, root)
            alleluia = root / "alleluia.md"
            original = "<!-- titre: Alléluia (Messe) -->\nAlléluia !"
            alleluia.write_text(original, encoding="utf-8")
            other = root / "chant.md"
            other.write_text("Paroles du chant", encoding="utf-8")
            songs = [("Entrée", other), catalog[mass.key], ("Alléluia (Messe)", alleluia), ("Envoi", other)]
            moments = ["", "Psaume", "Acclamation de l’Évangile", ""]
            html = create_song_sheet(mass.title, songs, moments=moments).decode()
            sections = html.split('<section ')[1:]
            self.assertNotIn(f"<strong>{intro}</strong>", sections[1])
            self.assertEqual(sections[2].count(f"<strong>{intro}</strong>"), 1)
            self.assertLess(sections[2].index("Alléluia !"), sections[2].index(f"<strong>{intro}</strong>"))
            restored = psalm_catalog(aelf_psalms_from_contents(html), root / "restored")
            reopened_songs = [songs[0], restored[mass.key], *songs[2:]]
            self.assertEqual(create_song_sheet(mass.title, reopened_songs, moments=moments).decode(), html)
            pdf, _ = create_print_song_sheet(mass.title, songs, moments=moments)
            with pymupdf.open(stream=pdf, filetype="pdf") as document:
                text = "\n".join(page.get_text() for page in document)
                self.assertEqual(text.count(intro), 1)
                self.assertLess(text.index("Alléluia !"), text.index(intro))
                spans = [span for page in document for block in page.get_text("dict")["blocks"]
                         if "lines" in block for line in block["lines"] for span in line["spans"]]
                self.assertTrue(any(intro in span["text"] and "Bold" in span["font"] for span in spans))
            pptx, _ = create_presentation(songs, moments=moments)
            presentation = Presentation(BytesIO(pptx))
            text = ["\n".join(shape.text for shape in slide.shapes if shape.has_text_frame)
                    for slide in presentation.slides]
            self.assertEqual(text.count(intro), 1)
            self.assertEqual(text.index(intro), text.index("Alléluia !") + 1)
            self.assertEqual(alleluia.read_text(encoding="utf-8"), original)
            hidden = create_song_sheet(mass.title, songs, moments=["", "Psaume", "Communion", ""]).decode()
            self.assertNotIn(f"<strong>{intro}</strong>", hidden)

    def test_gospel_directly_after_psalm_is_only_announced_after_acclamation(self):
        payload = response()
        intro = "Évangile de Jésus Christ selon saint Luc"
        payload["messes"][0]["lectures"].append({"type": "evangile", "intro_lue": intro})
        mass, = parse_aelf_response(payload, DAY)
        self.assertIn("evangile_intro:", mass.markdown)
        self.assertFalse(any(part.kind == "lecture" for part in build_song_parts(mass.markdown)))
        payload["messes"][0]["lectures"][-1]["intro_lue"] = None
        mass, = parse_aelf_response(payload, DAY)
        self.assertNotIn("evangile_intro:", mass.markdown)

    def test_adjacent_reading_introductions_surround_selected_psalm_in_all_exports(self):
        import pymupdf
        from pptx import Presentation
        from app import create_presentation
        from scripts.print_song_sheet import create_print_song_sheet

        payload = response()
        before = "Lecture du livre des Proverbes"
        after = "Lecture de la première lettre de saint Paul apôtre aux Thessaloniciens"
        psalm = payload["messes"][0]["lectures"][0]
        payload["messes"][0]["lectures"] = [
            {"type": "lecture_1", "intro_lue": before}, psalm,
            {"type": "lecture_2", "intro_lue": f"<p>{after}</p>"},
        ]
        mass, = parse_aelf_response(payload, DAY)
        with TemporaryDirectory() as directory:
            catalog = psalm_catalog({mass.key: mass.markdown}, Path(directory))
            song = catalog[mass.key]
            path = song[1]
            parts = selected_song_parts(path, ["C2"])
            self.assertEqual([part.identifier for part in parts], ["L1", "R", "C2", "R", "L2"])
            self.assertEqual(parts[0].text, f"**{before}**")
            self.assertEqual(parts[-1].text, f"**{after}**")
            self.assertEqual([part.identifier for part in selected_song_parts(path, [])], ["L1", "R", "L2"])
            html = create_song_sheet(mass.title, [song], verses=[["C2"]]).decode()
            self.assertLess(html.index(f"<strong>{before}</strong>"), html.index('<h2 id="titre-1">'))
            self.assertGreater(html.index(f"<strong>{after}</strong>"), html.index("Ta femme sera dans ta maison"))
            restored = psalm_catalog(aelf_psalms_from_contents(html), Path(directory) / "restored")
            self.assertEqual(selected_song_parts(restored[mass.key][1], ["C2"]), parts)
            pdf, _ = create_print_song_sheet(mass.title, [song], verses=[["C2"]])
            with pymupdf.open(stream=pdf, filetype="pdf") as document:
                spans = [span for page in document for block in page.get_text("dict")["blocks"]
                         if "lines" in block for line in block["lines"] for span in line["spans"]]
                text = "\n".join(span["text"] for span in spans)
                self.assertLess(text.index(before), text.index("Psaume 127"))
                self.assertLess(text.index("Ta femme"), text.index("Lecture de la première"))
                for span in spans:
                    if span["text"].startswith(("Lecture du livre", "Lecture de la première", "apôtre aux Thessaloniciens")):
                        self.assertIn("Bold", span["font"])
            pptx, _ = create_presentation([song], verses=[["C2"]])
            presentation = Presentation(BytesIO(pptx))
            first_runs = [run for shape in presentation.slides[0].shapes if shape.has_text_frame
                          for paragraph in shape.text_frame.paragraphs for run in paragraph.runs]
            self.assertEqual("".join(run.text for run in first_runs), before)
            self.assertTrue(all(run.font.bold for run in first_runs))

    def test_reading_introductions_are_optional_and_stay_with_their_mass(self):
        payload = response()
        psalm = payload["messes"][0]["lectures"][0]
        payload["messes"][0]["lectures"] = [
            {"type": "lecture_1", "intro_lue": None}, psalm,
            {"type": "lecture_2", "intro_lue": ""},
        ]
        other = deepcopy(payload["messes"][0])
        other["lectures"][0]["intro_lue"] = "Lecture de la seconde messe"
        payload["messes"].append(other)
        first, second = parse_aelf_response(payload, DAY)
        self.assertFalse(any(part.kind == "lecture" for part in build_song_parts(first.markdown)))
        self.assertEqual(build_song_parts(second.markdown)[0].text, "**Lecture de la seconde messe**")

    def test_user_response_extracts_title_refrain_stanzas_and_line_breaks(self):
        mass, = parse_aelf_response(response(), DAY)
        self.assertEqual(mass.title, "33ème dimanche du Temps Ordinaire (semaine I du Psautier) — Année A")
        self.assertEqual(mass.psalm_title, "Psaume 127 (128) — Heureux qui craint le Seigneur !")
        parts = build_song_parts(mass.markdown)
        self.assertEqual([part.identifier for part in parts], ["R", "C1", "R", "C2", "R", "C3", "R"])
        self.assertEqual(parts[1].text, "Heureux qui craint le Seigneur\net marche selon ses voies !\n"
                         "Tu te nourriras du travail de tes mains :\nHeureux es-tu ! À toi, le bonheur !")
        self.assertTrue(parts[3].text.startswith("Ta femme sera dans ta maison\n"))
        self.assertTrue(parts[5].text.startswith("Voilà comment sera béni\n"))
        self.assertNotIn("<p>", mass.markdown)
        self.assertEqual(html_paragraphs('<p>Texte &amp; <strong>paroles</strong><br/>suite</p><script>ignore</script>'),
                         ["Texte & paroles\nsuite"])

    def test_multiple_masses_and_canticle_have_distinct_choices(self):
        payload = response()
        other = deepcopy(payload["messes"][0])
        other["nom"] = "Messe de la veille"
        other["lectures"][0]["ref"] = "Is 12, 2-3"
        payload["messes"].append(other)
        masses = parse_aelf_response(payload, DAY)
        self.assertEqual(len(masses), 2)
        self.assertEqual(masses[1].name, "Messe de la veille")
        self.assertNotEqual(masses[0].key, masses[1].key)
        self.assertIn("Is 12", masses[1].psalm_title)

    def test_api_get_and_readable_failures(self):
        with patch("scripts.aelf.urlopen", return_value=BytesIO(FIXTURE.read_bytes())) as get:
            self.assertEqual(len(load_aelf_masses(DAY)), 1)
            self.assertEqual(get.call_args.args[0].full_url, api_url(DAY))
            self.assertEqual(api_url(DAY), "https://api.aelf.org/v1/messes/2026-11-15/france")
        for failure in (URLError("network unavailable"), TimeoutError("timeout")):
            with patch("scripts.aelf.urlopen", side_effect=failure), self.assertRaisesRegex(ValueError, "Impossible"):
                load_aelf_masses(DAY)
        with patch("scripts.aelf.urlopen", return_value=BytesIO(b"<html>Error</html>")), self.assertRaises(ValueError):
            load_aelf_masses(DAY)
        payload = response()
        payload["informations"]["date"] = "2026-11-14"
        with self.assertRaisesRegex(ValueError, "date"):
            parse_aelf_response(payload, DAY)
        for field in ("ref", "refrain_psalmique", "contenu"):
            payload = response()
            payload["messes"][0]["lectures"][0][field] = None
            with self.subTest(field=field), self.assertRaises(ValueError):
                parse_aelf_response(payload, DAY)
        payload = response()
        payload["messes"] = []
        with self.assertRaisesRegex(ValueError, "Aucun psaume"):
            parse_aelf_response(payload, DAY)

    def test_published_psalm_can_be_reopened_without_catalog_or_network(self):
        mass, = parse_aelf_response(response(), DAY)
        with TemporaryDirectory() as directory:
            catalog = psalm_catalog({mass.key: mass.markdown}, Path(directory))
            html = create_song_sheet(mass.title, [catalog[mass.key]], verses=[["C1", "C3"]]).decode()
        with TemporaryDirectory() as directory:
            restored = psalm_catalog(aelf_psalms_from_contents(html), Path(directory))
            self.assertEqual(songs_from_contents(html, restored), [mass.key])
            self.assertEqual(verses_from_contents(html, [mass.key], restored), [["C1", "C3"]])
            self.assertEqual(title_from_contents(html), mass.title)
            self.assertEqual(create_song_sheet(mass.title, [restored[mass.key]], verses=[["C1", "C3"]]).decode(), html)

    def test_ui_date_import_adds_psalm_exports_and_preserves_work_on_failure(self):
        mass, = parse_aelf_response(response(), DAY)
        root = Path(__file__).resolve().parents[1]
        catalog = {
            "entry": ("Entrée", root / "chants/habiter_le_seuil_de_ta_maison_seigneur.md"),
            "old": ("Ancien psaume", root / "chants/psaume_127.md"),
            "exit": ("Envoi", root / "chants/je_veux_chanter_ton amour_seigneur.md"),
        }
        with TemporaryDirectory() as directory, patch("app.ROOT", Path(directory)), \
                patch("app.song_catalog", side_effect=lambda: dict(catalog)), \
                patch("app.load_aelf_masses", return_value=[mass]) as fetch:
            app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20)
            app.session_state["song_order"] = ["entry", "old", "exit"]
            app.session_state["celebration_date"] = date(2026, 11, 14)
            app.run()
            fetch.assert_not_called()
            app.date_input(key="celebration_date").set_value(DAY).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input(key="celebration_title").value, mass.title)
            self.assertEqual(app.session_state["song_order"], ["entry", "old", "exit"])
            app.button(key="use_aelf_psalm").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["song_order"], ["entry", mass.key, "exit"])
            app.checkbox(key="sheet_verses_1_C2").uncheck().run()
            next(b for b in app.button if b.label == "Créer la feuille de chants").click().run()
            next(b for b in app.button if b.label == "Préparer pour GitHub Pages").click().run()
            document = app.session_state["pages_export"][1].document.decode()
            self.assertEqual(title_from_contents(document), mass.title)
            self.assertEqual(aelf_psalms_from_contents(document), {mass.key: mass.markdown})
            source = Path(directory) / "docs/paroisse/2026-11-15/index.html"
            source.parent.mkdir(parents=True)
            source.write_text(document, encoding="utf-8")
            reopened = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20).run()
            reopened.selectbox(key="existing_sheet_choice").select("paroisse/2026-11-15/index.html").run()
            self.assertFalse(reopened.exception)
            self.assertEqual(reopened.session_state["song_order"], ["entry", mass.key, "exit"])
            self.assertEqual(reopened.session_state["song_verses"][1], ["C1", "C3"])
            self.assertEqual(reopened.text_input(key="celebration_title").value, mass.title)
            app.text_input(key="celebration_title").set_value("Titre personnalisé").run()
            fetch.side_effect = ValueError("AELF indisponible")
            app.date_input(key="celebration_date").set_value(date(2026, 11, 22)).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input(key="celebration_title").value, "Titre personnalisé")
            self.assertEqual(app.session_state["song_order"], ["entry", mass.key, "exit"])
            self.assertIn("AELF indisponible", app.error[0].value)

    def test_ui_mass_choice_and_new_date_update_the_inserted_psalm(self):
        payload = response()
        second = deepcopy(payload["messes"][0])
        second["nom"] = "Autre messe"
        payload["messes"].append(second)
        variants = parse_aelf_response(payload, DAY)
        next_day = date(2026, 11, 22)
        next_payload = response()
        next_payload["informations"]["date"] = next_day.isoformat()
        next_mass, = parse_aelf_response(next_payload, next_day)
        root = Path(__file__).resolve().parents[1]
        catalog = {key: (key, root / name) for key, name in (
            ("entry", "chants/habiter_le_seuil_de_ta_maison_seigneur.md"),
            ("gloria", "chants/gloria_messe_de_st_augustin.md"),
            ("exit", "chants/je_veux_chanter_ton amour_seigneur.md"),
        )}
        with TemporaryDirectory() as directory, patch("app.ROOT", Path(directory)), \
                patch("app.song_catalog", side_effect=lambda: dict(catalog)), \
                patch("app.load_aelf_masses", return_value=variants) as fetch:
            app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20)
            app.session_state["song_order"] = list(catalog)
            app.session_state["celebration_date"] = DAY
            app.run()
            app.button(key="retrieve_aelf").click().run()
            app.button(key="use_aelf_psalm").click().run()
            self.assertEqual(app.session_state["song_order"], ["entry", "gloria", variants[0].key, "exit"])
            app.selectbox(key="aelf_mass_choice").select(variants[1].key).run()
            self.assertEqual(app.session_state["song_order"][2], variants[1].key)
            self.assertFalse(app.exception)
            fetch.return_value = [next_mass]
            app.date_input(key="celebration_date").set_value(next_day).run()
            app.run()  # Le sélecteur de variantes a disparu : le choix unique reste utilisable.
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["song_order"], ["entry", "gloria", next_mass.key, "exit"])
            app.button(key="use_aelf_psalm").click().run()
            self.assertEqual(len(app.session_state["song_order"]), 4)


if __name__ == "__main__":
    unittest.main()
