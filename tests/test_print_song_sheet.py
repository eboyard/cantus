from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pymupdf
from streamlit.testing.v1 import AppTest

from scripts.print_song_sheet import create_print_song_sheet


class PrintSongSheetTests(unittest.TestCase):
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
            with self.assertRaisesRegex(ValueError, "11 ou 12"):
                create_print_song_sheet("Messe", [("Vide", song)], font_size=8)

    def test_print_download_is_independent_and_tracks_text_size_and_selection(self):
        app = AppTest.from_string("from app import main\nmain()")
        app.session_state["song_order"] = ["chants/kyrie_messe_de_st_augustin.md"]
        app.run()
        next(button for button in app.button if button.label == "Créer la version à imprimer").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(app.session_state["generated_print_sheet"][1].startswith(b"%PDF-"))
        self.assertNotIn("generated_song_sheet", app.session_state)
        self.assertNotIn("generated_presentation", app.session_state)
        self.assertEqual(app.get("download_button")[0].proto.label, "Télécharger la version à imprimer (.pdf)")
        next(widget for widget in app.selectbox if widget.label == "Taille du texte imprimé").select(12).run()
        self.assertFalse(app.get("download_button"))
        next(button for button in app.button if button.label == "Créer la version à imprimer").click().run()
        self.assertFalse(app.error)
        app.text_input[0].set_value("Autre messe").run()
        self.assertFalse(app.get("download_button"))


if __name__ == "__main__":
    unittest.main()
