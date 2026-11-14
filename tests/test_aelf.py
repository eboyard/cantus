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
from scripts.sheet_library import aelf_psalms_from_contents, songs_from_contents, title_from_contents, verses_from_contents
from scripts.song_sheet import create_song_sheet


DAY = date(2026, 11, 15)
FIXTURE = Path(__file__).parent / "fixtures/aelf_2026_11_15.json"


def response():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class AelfTests(unittest.TestCase):
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
