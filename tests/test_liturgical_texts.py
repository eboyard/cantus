from datetime import date, timedelta
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from lxml import etree

from streamlit.testing.v1 import AppTest

from ui_helpers import item_widget_key, preparation_value, set_preparation_value

from scripts.aelf import parse_aelf_response
from scripts.liturgical_texts import reading_catalog, reading_documents
from scripts.sheet_library import reading_texts_from_contents, songs_from_contents
from scripts.song_types import MOMENTS, song_type
from scripts.word_song_sheet import create_word_song_sheet, NS


class LiturgicalTextTests(unittest.TestCase):
    def test_reading_types_and_legacy_titles_follow_liturgical_order(self):
        sequence = ("Gloire à Dieu", "Première lecture", "Psaume", "Deuxième lecture",
                    "Acclamation de l’Évangile", "Évangile", "Prières universelles")
        self.assertEqual(sorted(sequence, key=MOMENTS.index), list(sequence))
        for title in ("Première lecture", "Deuxième lecture", "Évangile", "Evangile"):
            expected = "Évangile" if title == "Evangile" else title
            for type_tag in ("", "<!-- type: -->\n", f"<!-- type: {title} -->\n"):
                self.assertEqual(song_type(f"<!-- titre: {title} -->\n{type_tag}Texte"), expected)
            self.assertEqual(song_type(f"<!-- titre: {title} -->\n<!-- type: Communion -->\nTexte"), "Communion")

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
            set_preparation_value(app, "song_order", ["entry"])
            app.run()
            app.date_input(key="celebration_date").set_value(day).run()
            self.assertEqual(preparation_value(app, "song_order"), ["entry"])
            keys = list(reading_documents(mass.markdown))
            for count, title in enumerate(("Première lecture", "Deuxième lecture", "Évangile"), 1):
                app.button(key=f"add_{title}").click().run()
                self.assertFalse(app.exception)
                self.assertEqual(preparation_value(app, "song_order"), ["entry", *keys[:count]])
                self.assertEqual(preparation_value(app, "song_moments")[-1], title)
            for position in (3, 2, 1):
                app.button(key=item_widget_key(app, f"up-{position}")).click().run()
            app.button(key=item_widget_key(app, "down-0")).click().run()
            app.button(key=item_widget_key(app, "remove-2")).click().run()
            expected = ["entry", keys[2], keys[1]]
            self.assertEqual(preparation_value(app, "song_order"), expected)
            next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
            self.assertFalse(app.exception)
            html = app.session_state["generated_song_sheet"][1].decode()
            self.assertNotIn("<strong>Lecture du livre des Proverbes</strong>", html)
            self.assertEqual(html.count('>Évangile</h2>'), 1)
            self.assertNotIn('<p class="moment">Évangile</p>', html)
            full_catalog = {**catalog, **reading_catalog(app.session_state["reading_texts"], root)}
            word = create_word_song_sheet("Messe", [full_catalog[key] for key in expected],
                                           moments=list(preparation_value(app, "song_moments")))
            with ZipFile(BytesIO(word)) as package:
                document = etree.fromstring(package.read("word/document.xml"))
            headings = ["".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
                        for paragraph in document.xpath("//w:p", namespaces=NS)]
            self.assertEqual(headings.count("Évangile"), 1)
            self.assertEqual(headings.count("Deuxième lecture"), 1)
            restored = reading_catalog(reading_texts_from_contents(html), root / "restored")
            self.assertEqual(songs_from_contents(html, {**catalog, **restored}), expected)
            path = root / "docs/paroisse/2026-11-15/index.html"
            path.parent.mkdir(parents=True)
            path.write_text(html, encoding="utf-8")
            reopened = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20).run()
            reopened.selectbox(key="existing_sheet_choice").select("paroisse/2026-11-15/index.html").run()
            self.assertFalse(reopened.exception)
            self.assertEqual(preparation_value(reopened, "song_order"), expected)
            self.assertEqual(preparation_value(reopened, "song_moments")[1:], ["Évangile", "Deuxième lecture"])
            reopened.button(key=item_widget_key(reopened, "remove-1")).click().run()
            self.assertEqual(preparation_value(reopened, "song_order"), ["entry", keys[1]])

    def test_invalid_saved_text_is_rejected(self):
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                reading_catalog({"reading/../../outside": "Texte"}, Path(directory))
        with self.assertRaises(ValueError):
            reading_texts_from_contents('<section id="chant-1" data-song-key="reading/invalid" data-reading-text="Texte">')
