from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class LyricsTests(unittest.TestCase):
    def test_consultation_preserves_preparation_and_follows_projection_order(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "chant.md"
            song.write_text(
                "<!-- titre: Chant -->\n<!-- ordre: C1 R C2 R -->\n"
                "<!-- refrain -->\n**Refrain**\nDeuxième ligne\n---\n"
                "Premier couplet\n---\nDeuxième couplet", encoding="utf-8",
            )
            catalog = {"b": ("Zèbre", song), "a": ("Chant", song)}
            with patch("app.song_catalog", return_value=catalog):
                app = AppTest.from_string("from app import show_lyrics\nshow_lyrics()")
                app.session_state["song_order"] = ["b", "b"]
                app.run()
                self.assertFalse(app.exception)
                self.assertEqual(app.selectbox[0].options, ["Chant", "Zèbre"])
                self.assertIsNone(app.selectbox[0].value)
                app.selectbox(key="lyrics_song").select("a").run()
                self.assertFalse(app.exception)
                self.assertEqual([item.value for item in app.markdown], [
                    "Premier couplet", "**Refrain**  \nDeuxième ligne",
                    "Deuxième couplet", "**Refrain**  \nDeuxième ligne",
                ])
                self.assertEqual(app.session_state["song_order"], ["b", "b"])
                app.selectbox(key="lyrics_song").select("b").run()
                self.assertEqual(app.subheader[0].value, "Zèbre")

    def test_empty_catalog_is_explained(self):
        with patch("app.song_catalog", return_value={}):
            app = AppTest.from_string("from app import show_lyrics\nshow_lyrics()").run()
            self.assertFalse(app.exception)
            self.assertIn("Aucun chant", app.info[0].value)

    def test_missing_invalid_and_empty_lyrics_are_explained(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "chant.md"
            with patch("app.song_catalog", return_value={"a": ("Chant", path)}):
                app = AppTest.from_string("from app import show_lyrics\nshow_lyrics()").run()
                app.selectbox[0].select("a").run()
                self.assertFalse(app.exception)
                self.assertIn("Impossible de lire", app.error[0].value)
                path.write_text("<!-- ordre: C2 -->\nCouplet unique", encoding="utf-8")
                app.run()
                self.assertFalse(app.exception)
                self.assertIn("C2", app.error[0].value)
                path.write_text("<!-- titre: Chant -->", encoding="utf-8")
                app.run()
                self.assertFalse(app.exception)
                self.assertIn("aucune parole", app.info[0].value)


if __name__ == "__main__":
    unittest.main()
