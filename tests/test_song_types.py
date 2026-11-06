from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pymupdf
from streamlit.testing.v1 import AppTest

from scripts.markdown_to_pptx import build_slides
from scripts.print_song_sheet import create_print_song_sheet
from scripts.song_types import MOMENTS, set_song_type, song_type


class SongTypesTests(unittest.TestCase):
    def test_known_types_and_ambiguous_titles(self):
        for title, moment in (("Gloria (Messe)", MOMENTS[2]),
                              ("Jésus, Verbe de Dieu (Kyrie)", MOMENTS[1]),
                              ("Sanctus", MOMENTS[7]), ("Anamnèse", MOMENTS[8]),
                              ("Agnus Dei", MOMENTS[9]), ("Psaume 62", MOMENTS[3]),
                              ("Alléluia (Messe de la grâce)", MOMENTS[4]),
                              ("Écoute-nous (Prière universelle)", MOMENTS[5]),
                              ("Psaume de la création", ""), ("Chante Alléluia au Seigneur", ""),
                              ("Je veux chanter ton amour", "")):
            with self.subTest(title=title):
                self.assertEqual(song_type(f"<!-- titre: {title} -->"), moment)

    def test_metadata_overrides_title_and_preserves_lyrics_order(self):
        original = "<!-- titre: Gloria -->\n<!-- ordre: C1 R -->\n<!-- refrain -->\nRefrain\n---\nCouplet"
        typed = set_song_type(original, MOMENTS[11])
        self.assertEqual(song_type(typed), MOMENTS[11])
        self.assertEqual(build_slides(typed), build_slides(original))
        self.assertEqual(song_type(set_song_type(typed, "")), "")
        self.assertEqual(set_song_type(typed, MOMENTS[2]).count("<!-- type:"), 1)

    def test_pdf_uses_catalog_defaults_and_per_occurrence_overrides(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "chant.md"
            path.write_text("<!-- titre: Gloria -->\nParoles", encoding="utf-8")
            default_pdf, _ = create_print_song_sheet("Messe", [("Gloria", path)])
            pdf, _ = create_print_song_sheet("Messe", [("Titre", path)] * 3,
                                           moments=[MOMENTS[0], MOMENTS[0], MOMENTS[11]])
            with pymupdf.open(stream=default_pdf, filetype="pdf") as doc:
                self.assertIn("3. Gloire à Dieu", doc[0].get_text())
            with pymupdf.open(stream=pdf, filetype="pdf") as doc:
                text = "".join(page.get_text() for page in doc)
                self.assertEqual(text.count("1. Chant d’entrée"), 1)
                self.assertEqual(text.count("12. Envoi"), 1)
                self.assertNotIn("Gloire à Dieu", text)
                self.assertEqual(text.count("Paroles"), 3)
            with self.assertRaises(ValueError):
                create_print_song_sheet("Messe", [("Titre", path)], moments=[])

    def test_occurrences_keep_their_moments_when_moved_and_removed(self):
        app = AppTest.from_string("from app import show_preparation\nshow_preparation()")
        app.session_state["song_order"] = ["chants/kyrie_messe_de_st_augustin.md"] * 2
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["song_moments"], [MOMENTS[1]] * 2)
        app.selectbox(key="sheet_moment_0").select(MOMENTS[0]).run()
        app.selectbox(key="sheet_moment_1").select(MOMENTS[11]).run()
        next(b for b in app.button if b.key == "up-1").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["song_moments"], [MOMENTS[11], MOMENTS[0]])
        next(b for b in app.button if b.label == "Créer la version à imprimer").click().run()
        self.assertTrue(app.get("download_button"))
        app.selectbox(key="sheet_moment_0").select("").run()
        self.assertFalse(app.get("download_button"))
        next(b for b in app.button if b.key == "remove-0").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["song_moments"], [MOMENTS[0]])

    def test_editor_saves_type_with_unchanged_lyrics(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "chant.md"
            original = "<!-- titre: Chant -->\nParoles"
            path.write_text(original, encoding="utf-8")
            with patch("app.song_catalog", return_value={"chants/chant.md": ("Chant", path)}), \
                    patch("app.github_setting", return_value="configured"), \
                    patch("app.load_song", return_value=(original, "sha")), \
                    patch("app.save_song", return_value="https://github.com/commit") as save:
                app = AppTest.from_string("from app import show_lyrics\nshow_lyrics()").run()
                app.selectbox(key="lyrics_song").select("chants/chant.md").run()
                next(b for b in app.button if b.label == "Modifier").click().run()
                app.selectbox(key="song_edit_type").select(MOMENTS[10])
                next(b for b in app.button if b.label == "Enregistrer").click().run()
                self.assertFalse(app.exception)
                saved = save.call_args.args[4]
                self.assertEqual(song_type(saved), MOMENTS[10])
                self.assertEqual(build_slides(saved), ["Paroles"])
                self.assertEqual(path.read_text(encoding="utf-8"), saved)


if __name__ == "__main__":
    unittest.main()
