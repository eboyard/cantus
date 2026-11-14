from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pymupdf
from streamlit.testing.v1 import AppTest

from scripts.print_song_sheet import create_print_song_sheet
from scripts.song_types import IMPLICIT_MOMENTS, MOMENTS


class PrintSongSheetTests(unittest.TestCase):
    def test_oversized_verse_continues_before_the_next_song(self):
        with TemporaryDirectory() as directory:
            long_song = Path(directory) / "long.md"
            long_song.write_text("\n".join(f"Ligne {i}" for i in range(160)), encoding="utf-8")
            next_song = Path(directory) / "suite.md"
            next_song.write_text("Paroles suivantes", encoding="utf-8")
            pdf, pages = create_print_song_sheet(
                "Messe", [("Chant long", long_song), ("Chant suivant", next_song)],
            )
        with pymupdf.open(stream=pdf, filetype="pdf") as document:
            self.assertGreater(pages, 1)
            text = "".join(page.get_text() for page in document)
            for i in range(160):
                self.assertIn(f"Ligne {i}\n", text)
            last_lyrics = max((number, word[3])
                              for number, page in enumerate(document)
                              for word in page.get_text("words") if word[4] == "Ligne")
            next_heading = next((number, rect.y0)
                                for number, page in enumerate(document)
                                for rect in page.search_for("Chant suivant"))
            self.assertGreater(next_heading, last_lyrics)

    def test_song_blocks_are_stacked_with_columns_inside_each_song(self):
        with TemporaryDirectory() as directory:
            songs = []
            for title, prefix in (("Entree", "Debut"), ("Gloria", "Gloire"), ("Sortie", "Fin")):
                path = Path(directory) / f"{prefix}.md"
                path.write_text("\n---\n".join(
                    "\n".join(f"{prefix} {section}-{line}" for line in range(4))
                    for section in range(4)
                ), encoding="utf-8")
                songs.append((title, path))
            for size in (9, 10, 11, 12):
                with self.subTest(font_size=size):
                    pdf, pages = create_print_song_sheet(
                        "Messe", songs, font_size=size,
                        moments=[MOMENTS[0], MOMENTS[2], MOMENTS[11]],
                    )
                    with pymupdf.open(stream=pdf, filetype="pdf") as document:
                        self.assertEqual(pages, 1)
                        page = document[0]
                        previous_bottom = 0
                        for (title, _), prefix, moment in zip(
                            songs, ("Debut", "Gloire", "Fin"),
                            (MOMENTS[0], MOMENTS[2], MOMENTS[11]),
                        ):
                            heading = page.search_for(title)[0]
                            if moment not in IMPLICIT_MOMENTS:
                                moment_box = page.search_for(moment)[0]
                                self.assertGreater(moment_box.y0, previous_bottom)
                                self.assertLess(moment_box.y0, heading.y0)
                            else:
                                self.assertFalse(page.search_for(moment))
                            self.assertLess(heading.x0, 100)
                            words = [word for word in page.get_text("words")
                                     if word[4] == prefix and word[1] > heading.y1]
                            self.assertEqual(len(words), 16)
                            self.assertEqual({word[0] > 290 for word in words}, {False, True})
                            self.assertGreater(min(word[1] for word in words), heading.y1)
                            previous_bottom = max(word[3] for word in words)
                            spans = [span for block in page.get_text("dict")["blocks"]
                                     if "lines" in block for line in block["lines"]
                                     for span in line["spans"] if prefix in span["text"]
                                     and span["bbox"][1] > heading.y1]
                            self.assertTrue(spans)
                            for span in spans:
                                self.assertAlmostEqual(span["size"], size)

    def test_print_type_errors_are_reported_and_logged_without_exposing_details(self):
        for error, expected_message in (
            (TypeError("create_print_song_sheet() got an unexpected keyword argument 'moments'"),
             "Le générateur PDF chargé ne prend pas en charge les rubriques de messe."),
            (TypeError("internal detail that must stay in the logs"),
             "La création du PDF a échoué à cause d'une erreur interne (TypeError)."),
        ):
            with self.subTest(error=error), \
                    patch("app.create_print_song_sheet", side_effect=error), \
                    patch("app.github_setting", return_value=""):
                app = AppTest.from_string(
                    "from app import show_preparation\nshow_preparation()", default_timeout=20,
                )
                app.session_state["song_order"] = ["chants/kyrie_messe_de_st_augustin.md"]
                app.run()
                with self.assertLogs("app", level="ERROR") as logs:
                    next(button for button in app.button
                         if button.label == "Créer la version à imprimer").click().run()
                self.assertFalse(app.exception)
                self.assertIn(expected_message, app.error[0].value)
                self.assertNotIn(str(error), app.error[0].value)
                self.assertIn(str(error), "\n".join(logs.output))
                self.assertFalse(app.get("download_button"))
                self.assertNotIn("generated_print_sheet", app.session_state)

    def test_refrain_written_once_without_losing_explicit_order_or_bridge(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "chant.md"
            song.write_text(
                "<!-- titre: Chant -->\n<!-- ordre: C2 R P1 R C1 R -->\n"
                "<!-- refrain -->\n**Grâce et paix**\n---\n"
                "<!-- couplet: C1 -->\nPremier couplet\n---\n"
                "<!-- couplet: C2 -->\nDeuxième couplet\n---\n"
                "<!-- pont: P1 -->\nLe pont", encoding="utf-8",
            )
            pdf, pages = create_print_song_sheet("Messe — fête", [("Entrée & louange", song)])
        with pymupdf.open(stream=pdf, filetype="pdf") as document:
            self.assertEqual(pages, len(document))
            self.assertAlmostEqual(document[0].rect.width, 595.276, places=2)
            self.assertAlmostEqual(document[0].rect.height, 841.89, places=2)
            text = "".join(page.get_text() for page in document)
            self.assertEqual(text.count("Grâce et paix"), 1)
            self.assertEqual(text.count("Refrain"), 2)
            self.assertLess(text.index("Deuxième couplet"), text.index("Grâce et paix"))
            self.assertLess(text.index("Le pont"), text.index("Premier couplet"))
            self.assertIn("2. Deuxième couplet", text)
            self.assertIn("Entrée & louange", text)
            self.assertNotIn("<!--", text)
            spans = [span for page in document for block in page.get_text("dict")["blocks"]
                     if "lines" in block for line in block["lines"] for span in line["spans"]]
            self.assertTrue(any("Bold" in span["font"] and "Grâce" in span["text"] for span in spans))

    def test_long_song_flows_through_both_columns_and_additional_pages(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "long.md"
            song.write_text("\n---\n".join(f"Couplet {i}\n" + "Une ligne de paroles\n" * 5 for i in range(50)), encoding="utf-8")
            pdf, pages = create_print_song_sheet("Messe", [("Chant long", song)], font_size=12)
        with pymupdf.open(stream=pdf, filetype="pdf") as document:
            self.assertGreater(pages, 1)
            text = "".join(page.get_text() for page in document)
            for i in range(50):
                self.assertIn(f"Couplet {i}\n", text)
            spans = [span for page in document for block in page.get_text("dict")["blocks"]
                     if "lines" in block for line in block["lines"] for span in line["spans"]
                     if "Une ligne" in span["text"]]
            self.assertTrue(any(span["bbox"][0] < 290 for span in spans))
            self.assertTrue(any(span["bbox"][0] > 300 for span in spans))
            for span in spans:
                self.assertAlmostEqual(span["size"], 12)
                self.assertGreater(span["bbox"][0], 30)
                self.assertLess(span["bbox"][2], 565)
                self.assertLess(span["bbox"][3], 810)

    def test_empty_or_invalid_content_is_rejected(self):
        with self.assertRaises(ValueError):
            create_print_song_sheet("Messe", [])
        with TemporaryDirectory() as directory:
            song = Path(directory) / "vide.md"
            song.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "vide.md"):
                create_print_song_sheet("Messe", [("Vide", song)])
            with self.assertRaisesRegex(ValueError, "9, 10, 11 ou 12"):
                create_print_song_sheet("Messe", [("Vide", song)], font_size=8)

    def test_print_download_is_independent_and_tracks_text_size_and_selection(self):
        app = AppTest.from_string("from app import main\nmain()")
        app.session_state["song_order"] = ["chants/kyrie_messe_de_st_augustin.md"]
        app.run()
        self.assertEqual(next(widget for widget in app.selectbox
                              if widget.label == "Taille du texte imprimé").value, 11)
        next(button for button in app.button if button.label == "Créer la version à imprimer").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(app.session_state["generated_print_sheet"][1].startswith(b"%PDF-"))
        self.assertNotIn("generated_song_sheet", app.session_state)
        self.assertNotIn("generated_presentation", app.session_state)
        self.assertEqual(app.get("download_button")[0].proto.label, "Télécharger la version à imprimer (.pdf)")
        for size in (9, 10, 12):
            next(widget for widget in app.selectbox
                 if widget.label == "Taille du texte imprimé").select(size).run()
            self.assertFalse(app.get("download_button"))
            next(button for button in app.button if button.label == "Créer la version à imprimer").click().run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertTrue(app.get("download_button"))
        app.text_input[0].set_value("Autre messe").run()
        self.assertFalse(app.get("download_button"))


if __name__ == "__main__":
    unittest.main()
