from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from scripts.song_sheet import create_song_sheet


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, text):
        self.text.append(text)


class SongSheetTests(unittest.TestCase):
    def test_song_order_refrains_bold_and_navigation(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "chant.md"
            song.write_text(
                "<!-- titre: Un titre -->\n<!-- ordre: C1 R C2 R -->\n"
                "<!-- refrain -->\n**Gloire à Toi !**\nAmen\n---\n"
                "<!-- couplet: C1 -->\nPremier couplet\n---\n"
                "<!-- couplet: C2 -->\nDeuxième couplet", encoding="utf-8",
            )
            html = create_song_sheet("Célébration", [("Entrée", song), ("Envoi", song)]).decode("utf-8")
        document = Document(html)
        ids = [attrs["id"] for _, attrs in document.tags if "id" in attrs]
        links = [attrs["href"] for tag, attrs in document.tags if tag == "a"]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(link[1:] in ids for link in links))
        self.assertLess(html.index('id="chant-1"'), html.index('id="chant-2"'))
        self.assertEqual(html.count("<strong>Gloire à Toi !</strong>"), 4)
        first_song = html.split('<section id="chant-1"')[1].split("</section>")[0]
        self.assertLess(first_song.index("Premier couplet"), first_song.index("Gloire à Toi !"))
        self.assertLess(first_song.index("Gloire à Toi !"), first_song.index("Deuxième couplet"))
        self.assertNotIn("<!--", html)
        self.assertIn(("meta", {"name": "viewport", "content": "width=device-width, initial-scale=1"}), document.tags)
        self.assertFalse(any(tag in ("script", "link", "img") for tag, _ in document.tags))

    def test_titles_and_lyrics_are_escaped(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "chant.md"
            lyrics = '<script>alert("test")</script> & **<b>Grâce</b>**'
            song.write_text(lyrics, encoding="utf-8")
            html = create_song_sheet("<Messe> & fête", [("<Chant>", song)]).decode("utf-8")
        document = Document(html)
        self.assertFalse(any(tag in ("script", "b", "messe", "chant") for tag, _ in document.tags))
        self.assertIn('<script>alert("test")</script> & ', "".join(document.text))
        self.assertIn("<strong>&lt;b&gt;Grâce&lt;/b&gt;</strong>", html)

    def test_empty_selection_or_song_is_rejected(self):
        with self.assertRaises(ValueError):
            create_song_sheet("Messe", [])
        with TemporaryDirectory() as directory:
            song = Path(directory) / "vide.md"
            song.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "vide.md"):
                create_song_sheet("Messe", [("Vide", song)])

    def test_download_is_independent_and_hidden_after_selection_changes(self):
        app = AppTest.from_string("from app import main\nmain()")
        app.session_state["song_order"] = ["chants/kyrie_messe_de_st_augustin.md"]
        app.run()
        next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        self.assertIn(b"<!doctype html>", app.session_state["generated_song_sheet"][1])
        self.assertEqual(app.get("download_button")[0].proto.label, "Télécharger la feuille de chants (.html)")
        self.assertNotIn("generated_presentation", app.session_state)
        app.text_input[0].set_value("Autre célébration").run()
        self.assertEqual(len(app.get("download_button")), 0)

    def test_empty_selection_and_generation_error(self):
        app = AppTest.from_string("from app import main\nmain()")
        app.run()
        self.assertTrue(next(button for button in app.button if button.label == "Créer la feuille de chants").disabled)
        app.session_state["song_order"] = ["chants/kyrie_messe_de_st_augustin.md"]
        app.run()
        with patch("app.create_song_sheet", side_effect=ValueError("Partie absente")):
            next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Partie absente", app.error[0].value)
        self.assertEqual(len(app.get("download_button")), 0)


if __name__ == "__main__":
    unittest.main()
