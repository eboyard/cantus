import unittest

from scripts.markdown_to_pptx import BACKGROUND_COLOR, build_slides, convert, read_slides, read_index_slides
from pptx import Presentation
from pathlib import Path
from tempfile import TemporaryDirectory


class RefrainTests(unittest.TestCase):
    def test_unmarked_song_keeps_original_order(self):
        self.assertEqual(build_slides("A\n---\nB\n---\nC"), ["A", "B", "C"])

    def test_refrain_between_verses(self):
        song = "<!-- refrain -->\nR\n---\nA\n---\nB\n---\nC"
        self.assertEqual(build_slides(song), ["R", "A", "R", "B", "R", "C"])

    def test_bridge_is_not_a_verse(self):
        song = "<!-- refrain -->\nR\n---\nA\n---\nB\n---\n<!-- pont -->\nP"
        self.assertEqual(build_slides(song), ["R", "A", "R", "B", "P"])

    def test_explicit_verse_markers_and_windows_newlines(self):
        song = "\r\n<!-- Refrain -->\r\nR\r\n --- \r\n<!-- couplet -->\r\nA\r\n---\r\nB\r\n---\r\n"
        self.assertEqual(build_slides(song), ["R", "A", "R", "B"])

    def test_refrain_already_between_verses_is_not_duplicated(self):
        self.assertEqual(build_slides("A\n---\n<!-- refrain -->\nR\n---\nB"), ["A", "R", "B"])

    def test_empty_or_multiple_refrains_are_rejected(self):
        for song in ("<!-- refrain -->", "<!-- refrain -->\nR\n---\n<!-- refrain -->\nS"):
            with self.subTest(song=song), self.assertRaises(ValueError):
                build_slides(song)

    def test_saint_est_son_nom_has_four_verses_and_bridge(self):
        source = Path(__file__).resolve().parents[1] / "chants" / "saint_est_son_nom.md"
        slides = read_slides(source)
        self.assertEqual(len(slides), 9)
        self.assertEqual([slides[i] for i in (0, 2, 4, 6)], [slides[0]] * 4)
        self.assertTrue(slides[8].startswith("Crions de joie !"))
        self.assertFalse(any("<!--" in slide for slide in slides))


class IndexTests(unittest.TestCase):
    def test_index_order_refrains_and_missing_lyrics(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chant.md").write_text("<!-- refrain -->\nR\n---\nA\n---\nB", encoding="utf-8")
            (root / "fin.md").write_text("Fin", encoding="utf-8")
            index = root / "index.md"
            index.write_text(
                "| Ordre | Moment | Titre | Fichier |\n"
                "| --- | --- | --- | --- |\n"
                "| 1 | Entrée | Chant | [Markdown](chant.md) |\n"
                "| 2 | Psaume | Psaume 22 (23) | Aucun fichier existant |\n"
                "| 3 | Envoi | Fin | [Markdown](fin.md) |\n",
                encoding="utf-8",
            )
            self.assertEqual(read_index_slides(index), ["R", "A", "R", "B", "", "Psaume 22 (23)", "", "Fin"])
            destination = root / "presentation.pptx"
            self.assertEqual(convert(index, destination, from_index=True), 8)
            presentation = Presentation(destination)
            self.assertEqual(len(presentation.slides), 8)
            for position in (4, 6):
                slide = presentation.slides[position]
                self.assertEqual(len(slide.shapes), 0)
                self.assertEqual(slide.background.fill.fore_color.rgb, BACKGROUND_COLOR)

    def test_broken_link_is_an_error(self):
        with TemporaryDirectory() as directory:
            index = Path(directory) / "index.md"
            index.write_text("| 1 | Entrée | Chant | [Markdown](absent.md) |", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                read_index_slides(index)

    def test_empty_index_is_an_error(self):
        with TemporaryDirectory() as directory:
            index = Path(directory) / "index.md"
            index.write_text("# Index sans chants", encoding="utf-8")
            with self.assertRaises(ValueError):
                read_index_slides(index)


if __name__ == "__main__":
    unittest.main()
