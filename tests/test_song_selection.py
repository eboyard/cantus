from pathlib import Path
from io import BytesIO
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pymupdf
from pptx import Presentation
from streamlit.testing.v1 import AppTest

from scripts.song_selection import selected_song_parts
from scripts.song_sheet import create_song_sheet
from scripts.print_song_sheet import create_print_song_sheet


SONG = (
    "<!-- titre: Chant -->\n<!-- ordre: C1 R C2 R P1 C3 R -->\n"
    "<!-- couplet: C1 -->\nPremier couplet\n---\n"
    "<!-- refrain -->\n**Refrain chanté**\n---\n"
    "<!-- couplet: C2 -->\nDeuxième couplet\n---\n"
    "<!-- pont: P1 -->\nPont chanté\n---\n"
    "<!-- couplet: C3 -->\nTroisième couplet"
)


class SongSelectionTests(unittest.TestCase):
    def test_filter_preserves_order_bridge_and_refrains_without_changing_source(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "chant.md"
            song.write_text(SONG, encoding="utf-8")
            self.assertEqual([p.identifier for p in selected_song_parts(song, ["C3", "C1"])],
                             ["C1", "R", "P1", "C3", "R"])
            self.assertEqual([p.identifier for p in selected_song_parts(song, [])], ["R", "P1"])
            with self.assertRaisesRegex(ValueError, "n'existent plus"):
                selected_song_parts(song, ["C9"])
            self.assertEqual(song.read_text(encoding="utf-8"), SONG)

    def test_default_order_and_refrain_only_selection(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "chant.md"
            song.write_text("<!-- refrain -->\nRefrain\n---\nPremier\n---\nSecond", encoding="utf-8")
            self.assertEqual([p.identifier for p in selected_song_parts(song, ["C2"])], ["R", "C2"])
            self.assertEqual([p.identifier for p in selected_song_parts(song, [])], ["R"])
            self.assertEqual(selected_song_parts(song), selected_song_parts(song, ["C1", "C2"]))

    def test_html_and_pdf_keep_selected_verses_with_original_numbers(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "chant.md"
            song.write_text(SONG, encoding="utf-8")
            songs = [("Chant", song)]
            html = create_song_sheet("Messe", songs, verses=[["C1", "C3"]]).decode()
            pdf, _ = create_print_song_sheet("Messe", songs, verses=[["C1", "C3"]])
            with pymupdf.open(stream=pdf, filetype="pdf") as document:
                text = "".join(page.get_text() for page in document)
            for output in (html, text):
                self.assertIn("Premier couplet", output)
                self.assertIn("Troisième couplet", output)
                self.assertNotIn("Deuxième couplet", output)
                self.assertIn("Pont chanté", output)
                self.assertIn("Refrain chanté", output)
            self.assertIn("3.", text)
            for generator in (create_song_sheet, create_print_song_sheet):
                with self.assertRaisesRegex(ValueError, "chaque chant"):
                    generator("Messe", songs, verses=[])

    def test_ui_selection_moves_with_each_occurrence_and_reaches_publication(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            song = root / "chant.md"
            song.write_text(SONG, encoding="utf-8")
            with patch("app.ROOT", root), patch("app.song_catalog", return_value={"a": ("Chant", song)}):
                app = AppTest.from_string("from app import main\nmain()", default_timeout=15)
                app.session_state["song_order"] = ["a", "a"]
                app.run()
                self.assertTrue(all(app.checkbox(key=f"sheet_verses_{position}_{identifier}").value
                                    for position in (0, 1) for identifier in ("C1", "C2", "C3")))
                app.checkbox(key="sheet_verses_0_C2").uncheck()
                app.checkbox(key="sheet_verses_0_C3").uncheck().run()
                app.checkbox(key="sheet_verses_1_C1").uncheck()
                app.checkbox(key="sheet_verses_1_C2").uncheck().run()
                app.button(key="down-0").click().run()
                self.assertEqual(app.session_state["song_verses"], [["C3"], ["C1"]])
                self.assertTrue(app.checkbox(key="sheet_verses_0_C3").value)
                self.assertFalse(app.checkbox(key="sheet_verses_0_C1").value)
                self.assertTrue(app.checkbox(key="sheet_verses_1_C1").value)
                next(b for b in app.button if b.label == "Créer le PowerPoint").click().run()
                data, count = app.session_state["generated_presentation"][1:]
                presentation = Presentation(BytesIO(data))
                projected = ["\n".join(shape.text for shape in slide.shapes if shape.has_text_frame)
                             for slide in presentation.slides]
                self.assertEqual(projected, ["Pont chanté", "Troisième couplet", "Refrain chanté", "",
                                             "Premier couplet", "Refrain chanté", "Pont chanté"])
                self.assertEqual(count, len(projected))
                next(b for b in app.button if b.label == "Créer la feuille de chants").click().run()
                next(b for b in app.button if b.label == "Préparer pour GitHub Pages").click().run()
                for document in (app.session_state["generated_song_sheet"][1],
                                 app.session_state["pages_export"][1].document):
                    sections = document.decode().split('<section ')[1:]
                    self.assertIn("Troisième couplet", sections[0])
                    self.assertNotIn("Premier couplet", sections[0])
                    self.assertIn("Premier couplet", sections[1])
                    self.assertNotIn("Troisième couplet", sections[1])
                    self.assertNotIn("Deuxième couplet", document.decode())
                next(b for b in app.button if b.label == "Créer la version à imprimer").click().run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                app.checkbox(key="sheet_verses_0_C3").uncheck()
                app.checkbox(key="sheet_verses_0_C1").check()
                app.checkbox(key="sheet_verses_0_C2").check().run()
                self.assertEqual(len(app.get("download_button")), 0)
                next(b for b in app.button if b.label == "Créer le PowerPoint").click().run()
                updated = Presentation(BytesIO(app.session_state["generated_presentation"][1]))
                updated_text = "\n".join(shape.text for slide in updated.slides
                                         for shape in slide.shapes if shape.has_text_frame)
                self.assertIn("Deuxième couplet", updated_text)
                self.assertNotIn("Troisième couplet", updated_text)
                self.assertFalse(any(b.label == "Publier sur GitHub Pages" for b in app.button))
                app.button(key="remove-0").click().run()
                self.assertEqual(app.session_state["song_verses"], [["C1"]])
                self.assertTrue(app.checkbox(key="sheet_verses_0_C1").value)
                self.assertFalse(app.checkbox(key="sheet_verses_0_C2").value)
                self.assertEqual(song.read_text(encoding="utf-8"), SONG)


if __name__ == "__main__":
    unittest.main()
