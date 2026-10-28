import base64
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from streamlit.testing.v1 import AppTest

from scripts.markdown_to_pptx import build_slides
from scripts.song_editor import SongDraft, load_song, parse_song, save_song, serialize_song


class SongEditorTests(unittest.TestCase):
    def test_metadata_preserves_order_and_does_not_enter_projection(self):
        lyrics = "<!-- ordre: C1 R -->\n<!-- refrain -->\nRefrain\n---\n<!-- couplet: C1 -->\nCouplet"
        draft = SongDraft("Été", lyrics, "Auteur", "Do Sol\nFa Do", "Do", "Licence\nSource")
        document = serialize_song(draft)
        self.assertEqual(parse_song(document), draft)
        self.assertEqual(build_slides(document), ["Couplet", "Refrain"])

    def test_existing_catalog_round_trips_without_changing_projection(self):
        for path in (Path(__file__).resolve().parents[1] / "chants").rglob("*.md"):
            with self.subTest(song=path.name):
                document = path.read_text(encoding="utf-8-sig")
                draft = parse_song(document, path.stem)
                self.assertEqual(build_slides(serialize_song(draft)), build_slides(document))

    def test_invalid_draft_is_rejected(self):
        for draft in (SongDraft("", "texte"), SongDraft("A\nB", "texte"),
                      SongDraft("Titre", ""), SongDraft("Titre", "<!-- ordre: C2 -->\nTexte"),
                      SongDraft("Titre", "Texte", information="-->\nTexte")):
            with self.subTest(draft=draft), self.assertRaises(ValueError):
                serialize_song(draft)

    @patch("scripts.song_editor._request")
    def test_load_and_save_use_branch_snapshot_and_utf8(self, request):
        document = "<!-- titre: Été -->\nParoles\n"
        request.return_value = {"type": "file", "encoding": "base64", "sha": "a" * 40,
                                "content": base64.b64encode(document.encode()).decode()}
        self.assertEqual(load_song("token", "owner/repo", "edit/songs", "chants/été.md"), (document, "a" * 40))
        self.assertIn("ref=edit%2Fsongs", request.call_args.args[1])
        request.return_value = {"commit": {"sha": "b" * 40}}
        url = save_song("token", "owner/repo", "edit/songs", "chants/été.md", document, "a" * 40)
        self.assertEqual(url, "https://github.com/owner/repo/commit/" + "b" * 40)
        payload = request.call_args.args[3]
        self.assertEqual(payload["sha"], "a" * 40)
        self.assertEqual(payload["branch"], "edit/songs")
        self.assertEqual(base64.b64decode(payload["content"]).decode(), document)

    @patch("scripts.song_editor._request")
    def test_conflict_is_explained_without_retry(self, request):
        request.side_effect = HTTPError("url", 409, "conflict", {}, None)
        with self.assertRaisesRegex(ValueError, "changé sur GitHub"):
            save_song("secret", "owner/repo", "main", "chants/song.md", "texte", "a" * 40)
        self.assertEqual(request.call_count, 1)

    @patch("scripts.song_editor._request")
    def test_only_existing_carnet_paths_can_be_written(self, request):
        for path in ("../app.py", "chants/../app.md", "chants//test.md", "docs/test.md"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                save_song("token", "owner/repo", "main", path, "texte", "a" * 40)
        request.assert_not_called()

    def test_simplified_form_saves_without_code_and_preserves_existing_metadata(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "song.md"
            song.write_text(serialize_song(SongDraft("Chant", "Ancien", "Auteur", "Do Sol", "Do", "Licence")), encoding="utf-8")
            settings = {"token": "token", "repository": "owner/repo", "branch": "main"}
            with patch("app.song_catalog", return_value={"chants/song.md": ("Chant", song)}), \
                    patch("app.github_setting", side_effect=lambda name, default="": settings.get(name, default)), \
                    patch("app.load_song", return_value=(song.read_text(encoding="utf-8"), "a" * 40)), \
                    patch("app.save_song", return_value="https://github.com/owner/repo/commit/" + "b" * 40) as save, \
                    patch("app.visual_song_editor", return_value=("Ancien", "")) as visual:
                app = AppTest.from_string("from app import show_lyrics\nshow_lyrics()").run()
                app.session_state["song_order"] = ["chants/song.md"]
                app.selectbox[0].select("chants/song.md").run()
                next(button for button in app.button if button.label == "Modifier").click().run()
                self.assertEqual([field.label for field in app.text_input], ["Titre du chant"])
                self.assertFalse(app.text_area)
                visual.return_value = ("**Nouveau** <u>texte</u>", "save")
                app.run()
                self.assertFalse(app.exception)
                save.assert_called_once()
                self.assertEqual(parse_song(song.read_text(encoding="utf-8")), SongDraft("Chant", "**Nouveau** <u>texte</u>", "Auteur", "Do Sol", "Do", "Licence"))
                self.assertEqual(app.session_state["song_order"], ["chants/song.md"])
                self.assertIn("enregistré", app.success[0].value)

    def test_conflict_retains_draft_and_cancel_preserves_local_file(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "song.md"
            original = "<!-- titre: Chant -->\nAncien"
            song.write_text(original, encoding="utf-8")
            settings = {"token": "token", "repository": "owner/repo", "branch": "main"}
            with patch("app.song_catalog", return_value={"chants/song.md": ("Chant", song)}), \
                    patch("app.github_setting", side_effect=lambda name, default="": settings.get(name, default)), \
                    patch("app.load_song", return_value=(original, "a" * 40)), \
                    patch("app.save_song", side_effect=ValueError("Le chant a changé sur GitHub.")), \
                    patch("app.visual_song_editor", return_value=("Ancien", "")) as visual:
                app = AppTest.from_string("from app import show_lyrics\nshow_lyrics()").run()
                app.selectbox[0].select("chants/song.md").run()
                next(button for button in app.button if button.label == "Modifier").click().run()
                visual.return_value = ("Mon brouillon", "save")
                app.run()
                self.assertFalse(app.exception)
                self.assertIn("changé", app.error[0].value)
                self.assertIn("song_editor", app.session_state)
                self.assertEqual(song.read_text(encoding="utf-8"), original)
                visual.return_value = ("Mon brouillon", "cancel")
                app.run()
                self.assertFalse(app.exception)
                self.assertFalse(app.text_area)
                self.assertEqual(song.read_text(encoding="utf-8"), original)

    def test_missing_configuration_disables_editor(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "song.md"
            song.write_text("Paroles", encoding="utf-8")
            with patch("app.song_catalog", return_value={"chants/song.md": ("Chant", song)}), \
                    patch("app.github_setting", return_value=""), patch("app.load_song") as load:
                app = AppTest.from_string("from app import show_lyrics\nshow_lyrics()").run()
                app.selectbox[0].select("chants/song.md").run()
                self.assertTrue(next(button for button in app.button if button.label == "Modifier").disabled)
                load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
