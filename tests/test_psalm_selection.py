from datetime import date
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from lxml import etree
from pptx import Presentation
from streamlit.testing.v1 import AppTest

from scripts.aelf import parse_aelf_response
from scripts.preparation_store import encode_preparation, decode_preparation, load_preparation
from scripts.psautier import parse_psalm
from scripts.sheet_library import verses_from_contents
from scripts.song_selection import selected_song_parts
from scripts.song_sheet import create_song_sheet
from scripts.word_song_sheet import create_word_song_sheet, NS


ROOT = Path(__file__).resolve().parents[1]
PSALM = ("<!-- titre: Psaume 150 -->\n\n**<u>Alpha</u>** première ligne\nFin alpha\n\n---\n\n"
         "Beta deuxième strophe\nFin beta\n\n---\n\nGamma troisième strophe\nFin gamma\n")


class PsalmSelectionTests(unittest.TestCase):
    def test_catalog_psalms_with_separators_and_blank_lines_are_selectable_without_changing_sources(self):
        for filename, count in (("psaume_127.md", 3), ("psaume_22_23.md", 5)):
            with self.subTest(filename=filename):
                path = ROOT / "chants" / filename
                original = path.read_bytes()
                parts = selected_song_parts(path)
                self.assertEqual([part.identifier for part in parts], [f"C{i}" for i in range(1, count + 1)])
                self.assertTrue(all(part.selectable for part in parts))
                # Les anciens exports enregistraient [] pour ces psaumes.
                self.assertEqual(selected_song_parts(path, []), parts)
                self.assertEqual(selected_song_parts(path, ["C2"]), [parts[1]])
                self.assertEqual(path.read_bytes(), original)

    def test_partial_psalm_is_identical_in_html_word_and_powerpoint_and_retains_formatting(self):
        from app import create_presentation
        with TemporaryDirectory() as folder:
            path = Path(folder) / "psaume.md"
            path.write_text(PSALM, encoding="utf-8")
            songs, choices = [("Psaume 150", path)], [["C1", "C3"]]
            html = create_song_sheet("Messe", songs, moments=["Psaume"], verses=choices).decode()
            word = create_word_song_sheet("Messe", songs, moments=["Psaume"], verses=choices)
            with ZipFile(BytesIO(word)) as package:
                doc = etree.fromstring(package.read("word/document.xml"))
            pptx, _ = create_presentation(songs, moments=["Psaume"], verses=choices)
            slides = Presentation(BytesIO(pptx))
            slide_text = " ".join(shape.text for slide in slides.slides for shape in slide.shapes if shape.has_text_frame)
            word_text = " ".join(doc.xpath("//w:t/text()", namespaces=NS))
            for output in (html, word_text, slide_text):
                self.assertIn("Alpha", output)
                self.assertIn("Gamma", output)
                self.assertNotIn("Beta", output)
            self.assertIn("<u>", html)
            self.assertTrue(doc.xpath("//w:r[w:rPr/w:b and w:rPr/w:u]/w:t[contains(text(), 'Alpha')]", namespaces=NS))
            self.assertTrue(any(run.font.bold and run.font.underline for slide in slides.slides
                                for shape in slide.shapes if shape.has_text_frame
                                for paragraph in shape.text_frame.paragraphs for run in paragraph.runs if "Alpha" in run.text))
            catalog = {"chants/psaume.md": songs[0]}
            self.assertEqual(verses_from_contents(html, list(catalog), catalog), choices)
            with self.assertRaisesRegex(ValueError, "versets sélectionnés"):
                selected_song_parts(path, ["C99"])

    def test_aelf_psalm_keeps_refrain_and_source_when_verses_are_removed(self):
        fixture = ROOT / "tests/fixtures/aelf_2026_11_15.json"
        mass, = parse_aelf_response(json.loads(fixture.read_text(encoding="utf-8")), date(2026, 11, 15))
        with TemporaryDirectory() as folder:
            path = Path(folder) / "aelf.md"
            path.write_text(mass.markdown, encoding="utf-8")
            full = selected_song_parts(path)
            chosen = selected_song_parts(path, ["C2"])
            self.assertTrue(any(part.kind == "refrain" for part in chosen))
            self.assertEqual({part.identifier for part in chosen if part.selectable}, {"C2"})
            self.assertTrue(all(part.kind == "refrain" for part in selected_song_parts(path, [])))
            self.assertLess(len(chosen), len(full))
            self.assertEqual(path.read_text(encoding="utf-8"), mass.markdown)

    def test_psautier_import_and_canticle_support_the_same_selection(self):
        document = ('<h1>Cantique</h1><h2>Titre</h2><table>'
                    '<tr><td></td><td>1</td><td>Première <b>strophe</b>.</td></tr>'
                    '<tr><td></td><td></td><td>&nbsp;</td></tr>'
                    '<tr><td></td><td>2</td><td>Deuxième <u>strophe</u>.</td></tr></table>')
        markdown = parse_psalm(document, "at40")
        with TemporaryDirectory() as folder:
            path = Path(folder) / "cantique.md"
            for text in (markdown, markdown.replace("type: Psaume", "type: Cantique")):
                path.write_text(text, encoding="utf-8")
                self.assertEqual([part.identifier for part in selected_song_parts(path)], ["C1", "C2"])
                self.assertEqual([part.text for part in selected_song_parts(path, ["C2"])], ["Deuxième <u>strophe</u>."])

    def test_implicit_psalm_with_explicit_order_keeps_part_identifiers_and_repetitions(self):
        markdown = "<!-- titre: Psaume 150 -->\n<!-- ordre: C2 C1 C2 -->\nAlpha\n---\nBeta"
        with TemporaryDirectory() as folder:
            path = Path(folder) / "psaume.md"
            path.write_text(markdown, encoding="utf-8")
            self.assertEqual([part.identifier for part in selected_song_parts(path)], ["C2", "C1", "C2"])
            self.assertEqual([part.text for part in selected_song_parts(path, ["C2"])], ["Beta", "Beta"])
            self.assertEqual(selected_song_parts(path, []), selected_song_parts(path))

    def test_ui_saves_independent_selections_per_occurrence_and_restores_after_reordering(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "chants").mkdir()
            path = root / "chants/psaume.md"
            path.write_text(PSALM, encoding="utf-8")
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"):
                script = "from app import show_preparation\nshow_preparation()"
                app = AppTest.from_string(script, default_timeout=20)
                app.session_state["song_order"] = ["chants/psaume.md"] * 2
                app.session_state["song_moments"] = ["Psaume"] * 2
                app.session_state["song_verses"] = [[], None]
                app.run()
                self.assertFalse(app.exception)
                self.assertEqual(sum(item.value == "Versets à garder" for item in app.caption), 2)
                app.checkbox(key="sheet_verses_0_C2").uncheck().run()
                app.checkbox(key="sheet_verses_1_C1").uncheck().run()
                app.button(key="down-0").click().run()
                self.assertEqual(app.session_state["song_verses"], [["C2", "C3"], ["C1", "C3"]])
                identifier = app.session_state["preparation_identifier"]
                saved = load_preparation(root / ".cantus-drafts", identifier)
                self.assertEqual(decode_preparation(encode_preparation(saved))["song_verses"], saved["song_verses"])
                restored = AppTest.from_string(script, default_timeout=20)
                restored.query_params["preparation"] = identifier
                restored.run()
                self.assertFalse(restored.exception)
                self.assertEqual(restored.session_state["song_verses"], saved["song_verses"])
                restored.checkbox(key="sheet_verses_0_C3").uncheck().run()
                self.assertTrue(restored.checkbox(key="sheet_verses_0_C2").disabled)
                self.assertFalse(restored.checkbox(key="sheet_verses_0_C1").disabled)
                restored.checkbox(key="sheet_verses_0_C1").check().run()
                for identifier in ("C1", "C2", "C3"):
                    restored.checkbox(key=f"sheet_verses_0_{identifier}").uncheck()
                restored.run()
                self.assertFalse(restored.exception)
                self.assertTrue(restored.session_state["song_verses"][0])
                self.assertEqual(path.read_text(encoding="utf-8"), PSALM)

    def test_ui_allows_keeping_only_refrain_even_with_one_verse(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "chants").mkdir()
            path = root / "chants/psaume.md"
            path.write_text("<!-- titre: Psaume 150 -->\n<!-- refrain -->\nRefrain gardé\n---\n"
                            "<!-- couplet: C1 -->\nVerset retiré", encoding="utf-8")
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"):
                app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20)
                app.session_state["song_order"] = ["chants/psaume.md"]
                app.run()
                checkbox = app.checkbox(key="sheet_verses_0_C1")
                self.assertFalse(checkbox.disabled)
                checkbox.uncheck().run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["song_verses"], [[]])
                preview = next(item for item in app.expander if item.label == "Aperçu des paroles")
                text = " ".join(item.value for item in preview.markdown)
                self.assertIn("Refrain gardé", text)
                self.assertNotIn("Verset retiré", text)


if __name__ == "__main__":
    unittest.main()
