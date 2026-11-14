from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pymupdf
from streamlit.testing.v1 import AppTest

from scripts.markdown_to_pptx import build_slides
from scripts.print_song_sheet import create_print_song_sheet
from scripts.song_types import MOMENTS, celebration_moments, set_song_type, song_type


class SongTypesTests(unittest.TestCase):
    def test_last_kyrie_is_not_relabelled_as_exit_in_html_pdf_or_saved_moments(self):
        from scripts.song_sheet import create_song_sheet
        from scripts.sheet_library import moments_from_contents

        with TemporaryDirectory() as directory:
            root = Path(directory)
            entry = root / "entree.md"
            kyrie = root / "kyrie.md"
            entry.write_text("Paroles d’entrée", encoding="utf-8")
            kyrie.write_text("<!-- titre: Kyrie -->\nKyrie eleison", encoding="utf-8")
            songs = [("Entrée", entry), ("Kyrie", kyrie)]
            catalog = {"a": songs[0], "k": songs[1]}
            html = create_song_sheet("Messe", songs).decode()
            self.assertNotIn('<p class="moment">Envoi</p>', html)
            self.assertIn('<p class="moment">Préparation pénitentielle</p>', html)
            pdf, _ = create_print_song_sheet("Messe", songs)
            with pymupdf.open(stream=pdf, filetype="pdf") as document:
                text = "\n".join(page.get_text() for page in document)
            self.assertNotIn("Envoi", text)
            self.assertIn("Préparation pénitentielle", text)
            import re
            legacy = create_song_sheet("Messe", songs, moments=["Chant d’entrée", "Envoi"]).decode()
            legacy = re.sub(r' data-song-moment="[^"]*"', "", legacy)
            self.assertEqual(moments_from_contents(legacy, ["a", "k"], catalog),
                             ["Chant d’entrée", "Préparation pénitentielle"])
            for choices in (["Communion", "Préparation pénitentielle"], ["", "Préparation pénitentielle"]):
                html = create_song_sheet("Messe", songs, moments=choices).decode()
                self.assertEqual(moments_from_contents(html, ["a", "k"], catalog), choices)
                self.assertNotIn('<p class="moment">Chant d’entrée</p>', html)
                self.assertNotIn('<p class="moment">Envoi</p>', html)
            published = root / "docs/paroisse/2026-11-14/index.html"
            published.parent.mkdir(parents=True)
            published.write_text(create_song_sheet("Messe", songs, moments=["Communion", "Préparation pénitentielle"]).decode(),
                                 encoding="utf-8")
            with patch("app.ROOT", root), patch("app.song_catalog", return_value=catalog):
                app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=15).run()
                app.selectbox(key="existing_sheet_choice").select("paroisse/2026-11-14/index.html").run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["song_moments"], ["Communion", "Préparation pénitentielle"])
                self.assertEqual(app.selectbox(key="sheet_moment_1").value, "Préparation pénitentielle")

    def test_boundary_defaults_do_not_override_known_moments(self):
        self.assertEqual(celebration_moments([]), [])
        self.assertEqual(celebration_moments([MOMENTS[2]]), [MOMENTS[2]])
        self.assertEqual(celebration_moments(["", ""]), [MOMENTS[0], MOMENTS[-1]])
        choices = [MOMENTS[2], MOMENTS[10], MOMENTS[7]]
        self.assertEqual(celebration_moments(choices), choices)
        self.assertEqual(choices, [MOMENTS[2], MOMENTS[10], MOMENTS[7]])

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
            default_pdf, _ = create_print_song_sheet("Messe", [("Gloria", path)] * 3)
            pdf, _ = create_print_song_sheet("Messe", [("Titre", path)] * 3,
                                           moments=[MOMENTS[0], MOMENTS[0], MOMENTS[11]])
            forced_pdf, _ = create_print_song_sheet("Messe", [("Titre", path)] * 3,
                                                  moments=[MOMENTS[7]] * 3)
            with pymupdf.open(stream=default_pdf, filetype="pdf") as doc:
                lines = doc[0].get_text().splitlines()
                for moment in (MOMENTS[0], MOMENTS[2], MOMENTS[-1]):
                    self.assertNotIn(moment, lines)
            with pymupdf.open(stream=forced_pdf, filetype="pdf") as doc:
                lines = doc[0].get_text().splitlines()
                for moment in (MOMENTS[0], MOMENTS[7], MOMENTS[-1]):
                    self.assertNotIn(moment, lines)
            with pymupdf.open(stream=pdf, filetype="pdf") as doc:
                text = "".join(page.get_text() for page in doc)
                self.assertEqual(text.splitlines().count("Chant d’entrée"), 1)
                self.assertEqual(text.splitlines().count("Envoi"), 1)
                self.assertNotIn("Gloire à Dieu", text)
                self.assertEqual(text.count("Paroles"), 3)
            with self.assertRaises(ValueError):
                create_print_song_sheet("Messe", [("Titre", path)], moments=[])

    def test_occurrences_keep_their_moments_when_moved_and_removed(self):
        app = AppTest.from_string("from app import show_preparation\nshow_preparation()")
        app.session_state["song_order"] = ["chants/kyrie_messe_de_st_augustin.md"] * 4
        app.run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["song_moments"], [MOMENTS[1]] * 4)
        self.assertFalse(app.selectbox(key="sheet_moment_0").disabled)
        self.assertFalse(app.selectbox(key="sheet_moment_3").disabled)
        self.assertEqual(app.selectbox(key="sheet_moment_0").value, MOMENTS[1])
        self.assertEqual(app.selectbox(key="sheet_moment_3").value, MOMENTS[1])
        app.selectbox(key="sheet_moment_1").select(MOMENTS[10]).run()
        app.selectbox(key="sheet_moment_2").select(MOMENTS[6]).run()
        next(b for b in app.button if b.key == "up-1").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="sheet_moment_0").value, MOMENTS[10])
        self.assertEqual(app.selectbox(key="sheet_moment_1").value, MOMENTS[1])
        self.assertEqual(app.selectbox(key="sheet_moment_2").value, MOMENTS[6])
        next(b for b in app.button if b.key == "down-2").click().run()
        self.assertEqual(app.selectbox(key="sheet_moment_2").value, MOMENTS[1])
        self.assertEqual(app.selectbox(key="sheet_moment_3").value, MOMENTS[6])
        next(b for b in app.button if b.label == "Créer la version à imprimer").click().run()
        self.assertTrue(app.get("download_button"))
        app.selectbox(key="sheet_moment_1").select("").run()
        self.assertFalse(app.get("download_button"))
        next(b for b in app.button if b.key == "remove-0").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="sheet_moment_0").value, "")
        self.assertEqual(app.selectbox(key="sheet_moment_2").value, MOMENTS[6])
        next(b for b in app.button if b.label == "Ajouter le chant").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="sheet_moment_2").value, MOMENTS[6])
        self.assertFalse(app.selectbox(key="sheet_moment_2").disabled)
        self.assertEqual(app.selectbox(key="sheet_moment_3").value, "")

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
