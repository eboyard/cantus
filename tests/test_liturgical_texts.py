from datetime import date, timedelta
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from scripts.aelf import parse_aelf_response
from scripts.liturgical_texts import reading_catalog, reading_documents
from scripts.sheet_library import reading_texts_from_contents, songs_from_contents


class LiturgicalTextTests(unittest.TestCase):
    def test_independent_add_move_remove_export_and_reopen_without_automatic_insertions(self):
        fixture = Path(__file__).parent / "fixtures/aelf_2026_11_15.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        readings = payload["messes"][0]["lectures"]
        readings.insert(0, {"type": "lecture_1", "intro_lue": "Lecture du livre des Proverbes"})
        readings.extend([
            {"type": "lecture_2", "intro_lue": "Lecture de saint Paul"},
            {"type": "evangile", "intro_lue": "Évangile de Jésus Christ selon saint Matthieu"},
        ])
        day = date(2026, 11, 15)
        mass, = parse_aelf_response(payload, day)
        entry = Path(__file__).resolve().parents[1] / "chants/habiter_le_seuil_de_ta_maison_seigneur.md"
        catalog = {"entry": ("Entrée", entry)}
        with TemporaryDirectory() as directory, patch("app.ROOT", Path(directory)), \
                patch("app.song_catalog", side_effect=lambda: dict(catalog)), \
                patch("app.load_aelf_masses", return_value=[mass]):
            root = Path(directory)
            app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20)
            app.session_state["celebration_date"] = day - timedelta(days=1)
            app.session_state["song_order"] = ["entry"]
            app.run()
            app.date_input(key="celebration_date").set_value(day).run()
            self.assertEqual(app.session_state["song_order"], ["entry"])
            keys = list(reading_documents(mass.markdown))
            for count, title in enumerate(("Première lecture", "Deuxième lecture", "Évangile"), 1):
                app.button(key=f"add_{title}").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["song_order"], ["entry", *keys[:count]])
            for position in (3, 2, 1):
                app.button(key=f"up-{position}").click().run()
            app.button(key="down-0").click().run()
            app.button(key="remove-2").click().run()
            expected = ["entry", keys[2], keys[1]]
            self.assertEqual(app.session_state["song_order"], expected)
            next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
            self.assertFalse(app.exception)
            html = app.session_state["generated_song_sheet"][1].decode()
            self.assertNotIn("<strong>Lecture du livre des Proverbes</strong>", html)
            restored = reading_catalog(reading_texts_from_contents(html), root / "restored")
            self.assertEqual(songs_from_contents(html, {**catalog, **restored}), expected)
            path = root / "docs/paroisse/2026-11-15/index.html"
            path.parent.mkdir(parents=True)
            path.write_text(html, encoding="utf-8")
            reopened = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20).run()
            reopened.selectbox(key="existing_sheet_choice").select("paroisse/2026-11-15/index.html").run()
            self.assertFalse(reopened.exception)
            self.assertEqual(reopened.session_state["song_order"], expected)
            self.assertEqual(reopened.session_state["song_moments"][1:], ["", ""])
            reopened.button(key="remove-1").click().run()
            self.assertEqual(reopened.session_state["song_order"], ["entry", keys[1]])

    def test_invalid_saved_text_is_rejected(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                reading_catalog({"reading/../../outside": "Texte"}, Path(directory))
        with self.assertRaises(ValueError):
            reading_texts_from_contents('<section id="chant-1" data-song-key="reading/invalid" data-reading-text="Texte">')
