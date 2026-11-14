from datetime import date
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
    def test_anamnesis_heading_is_implicit_on_phone_and_print(self):
        import pymupdf
        from scripts.print_song_sheet import create_print_song_sheet

        root = Path(__file__).resolve().parents[1]
        song = root / "chants/anamnèse_messe_de_st_augustin.md"
        songs = [("Entrée", song), ("Anamnèse (Messe de St Augustin)", song), ("Envoi", song)]
        moments = ["", "Anamnèse", ""]
        html = create_song_sheet("Messe", songs, moments=moments).decode()
        self.assertNotIn('<p class="moment">Anamnèse</p>', html)
        self.assertIn('Anamnèse (Messe de St Augustin)</h2>', html)
        pdf, _ = create_print_song_sheet("Messe", songs, moments=moments)
        with pymupdf.open(stream=pdf, filetype="pdf") as document:
            text = "".join(page.get_text() for page in document)
        self.assertEqual(text.count("Anamnèse"), 1)
        self.assertIn("Anamnèse (Messe de St Augustin)", text)

    def test_moments_follow_songs_with_automatic_entry_and_exit(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "chant.md"
            song.write_text("<!-- type: Psaume -->\nParoles", encoding="utf-8")
            songs = [("Chant", song)] * 4
            html = create_song_sheet("Messe", songs, moments=["", "Offertoire", "", ""]).decode()
            sections = html.split('<section ')[1:]
            for section, moment in zip(sections, ["Chant d’entrée", "Offertoire", "", "Envoi"]):
                if moment:
                    self.assertIn(f'<p class="moment">{moment}</p>', section)
                    self.assertLess(section.index('class="moment"'), section.index('<h2'))
                else:
                    self.assertNotIn('class="moment"', section)
            inferred = create_song_sheet("Messe", songs).decode()
            self.assertNotIn('<p class="moment">Psaume</p>', inferred)
            for invalid in ([""], ["", "<script>", "", ""]):
                with self.assertRaisesRegex(ValueError, "rubrique valide"):
                    create_song_sheet("Messe", songs, moments=invalid)

    def test_selected_moments_are_in_download_and_export_and_changes_invalidate_them(self):
        app = AppTest.from_string("from app import main\nmain()")
        app.session_state["song_order"] = ["chants/agnus_dei.md"] * 3
        app.run()
        app.selectbox(key="sheet_moment_1").select("Offertoire").run()
        next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
        downloaded = app.session_state["generated_song_sheet"][1].decode()
        next(button for button in app.button if button.label == "Préparer pour GitHub Pages").click().run()
        exported = app.session_state["pages_export"][1].document.decode()
        for html in (downloaded, exported):
            for moment in ("Chant d’entrée", "Offertoire", "Envoi"):
                self.assertIn(f'<p class="moment">{moment}</p>', html)
        app.selectbox(key="sheet_moment_1").select("Communion").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("download_button")), 0)
        self.assertFalse(any(button.label == "Publier sur GitHub Pages" for button in app.button))
        next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
        next(button for button in app.button if button.label == "Préparer pour GitHub Pages").click().run()
        self.assertFalse(app.exception)
        for html in (app.session_state["generated_song_sheet"][1].decode(),
                     app.session_state["pages_export"][1].document.decode()):
            self.assertIn('<p class="moment">Communion</p>', html)
            self.assertNotIn('<p class="moment">Offertoire</p>', html)

    def test_song_order_refrains_bold_without_contents(self):
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
        self.assertEqual(links, [])
        self.assertFalse(any(tag == "nav" for tag, _ in document.tags))
        self.assertNotIn("sommaire", html.lower())
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

    @patch("app.load_aelf_masses", side_effect=ValueError("Hors connexion pour ce test"))
    def test_download_contains_selected_date_and_is_hidden_when_date_changes(self, _fetch):
        app = AppTest.from_string("from app import main\nmain()")
        app.session_state["song_order"] = ["chants/kyrie_messe_de_st_augustin.md"]
        app.run()
        app.date_input(key="celebration_date").set_value(date(2026, 11, 15)).run()
        next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
        self.assertFalse(app.exception)
        html = app.session_state["generated_song_sheet"][1].decode("utf-8")
        self.assertIn("15/11/2026</h1>", html)
        app.date_input(key="celebration_date").set_value(date(2026, 11, 22)).run()
        self.assertEqual(len(app.get("download_button")), 0)
        next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
        self.assertIn("22/11/2026</h1>", app.session_state["generated_song_sheet"][1].decode("utf-8"))

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
