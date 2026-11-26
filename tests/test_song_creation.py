import base64
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from streamlit.testing.v1 import AppTest

from ui_helpers import preparation_value, set_preparation_value

from scripts.song_editor import create_song, new_song_path, parse_song
from scripts.song_types import MOMENTS, song_type


class SongCreationTests(unittest.TestCase):
    def test_filename_normalizes_accents_and_cannot_escape_catalog(self):
        self.assertEqual(new_song_path("Écoute, ô mon âme !"), "chants/ecoute_o_mon_ame.md")
        self.assertEqual(new_song_path("../../Un chant"), "chants/un_chant.md")
        with self.assertRaises(ValueError):
            new_song_path("!!!")

    @patch("scripts.song_editor._request")
    def test_create_sends_utf8_and_branch_without_overwrite_sha(self, request):
        document = "<!-- titre: Été -->\nParoles\n"
        request.return_value = {"commit": {"sha": "b" * 40}}
        url = create_song("token", "owner/repo", "songs/new", "chants/ete.md", document)
        method, endpoint, token, payload = request.call_args.args
        self.assertEqual((method, endpoint, token), ("PUT", "https://api.github.com/repos/owner/repo/contents/chants/ete.md", "token"))
        self.assertEqual(payload["branch"], "songs/new")
        self.assertNotIn("sha", payload)
        self.assertEqual(base64.b64decode(payload["content"]).decode(), document)
        self.assertEqual(url, "https://github.com/owner/repo/commit/" + "b" * 40)

    @patch("scripts.song_editor._request")
    def test_conflicts_never_retry_or_overwrite(self, request):
        for code in (409, 422):
            request.reset_mock()
            request.side_effect = HTTPError("url", code, "conflict", {}, None)
            with self.assertRaisesRegex(ValueError, "déjà"):
                create_song("token", "owner/repo", "main", "chants/song.md", "<!-- titre: Chant -->\nParoles")
            request.assert_called_once()

    @patch("scripts.song_editor._request")
    def test_invalid_creation_never_reaches_github(self, request):
        for path, document in (("../app.py", "Texte"), ("docs/test.md", "Texte"),
                               ("chants/song.md", "<!-- titre: Chant -->"),
                               ("chants/song.md", "Sans titre")):
            with self.subTest(path=path, document=document), self.assertRaises(ValueError):
                create_song("token", "owner/repo", "main", path, document)
        request.assert_not_called()

    def scenario(self, stack, *, configured=True):
        root = Path(stack.enter_context(TemporaryDirectory()))
        stack.enter_context(patch("app.ROOT", root))
        stack.enter_context(patch("app.SONGS_DIR", root / "chants"))
        settings = {"publish_password": "code-test", "token": "token" if configured else "", "repository": "owner/repo", "branch": "main"}
        stack.enter_context(patch("app.github_setting", side_effect=lambda name, default="": settings.get(name, default)))
        create = stack.enter_context(patch("app.create_song", return_value="https://github.com/owner/repo/commit/" + "b" * 40))
        app = AppTest.from_string("from app import show_lyrics\nshow_lyrics()").run()
        set_preparation_value(app, "song_order", ["chants/existing.md"])
        return root, create, app

    @staticmethod
    def click(app, label):
        if label == "Enregistrer":
            app.text_input(key="song_create_password").set_value("code-test")
        return next(button for button in app.button if button.label == label).click().run()

    def test_creation_from_empty_catalog_appears_selected_and_preserves_preparation(self):
        with ExitStack() as stack:
            root, create, app = self.scenario(stack)
            self.click(app, "Ajouter un chant")
            app.text_input[0].set_value("Écoute mon âme")
            app.text_area[0].set_value("<!-- refrain -->\n**Refrain**\n---\nUn couplet")
            app.selectbox[0].select(MOMENTS[0])
            self.click(app, "Enregistrer")
            self.assertFalse(app.exception)
            create.assert_called_once()
            self.assertEqual(create.call_args.args[:4], ("token", "owner/repo", "main", "chants/ecoute_mon_ame.md"))
            document = (root / "chants/ecoute_mon_ame.md").read_text(encoding="utf-8")
            self.assertEqual(parse_song(document).title, "Écoute mon âme")
            self.assertEqual(song_type(document), MOMENTS[0])
            self.assertEqual(app.selectbox[0].value, "chants/ecoute_mon_ame.md")
            self.assertEqual(preparation_value(app, "song_order"), ["chants/existing.md"])
            self.assertTrue(app.success)

    def test_errors_keep_draft_and_do_not_create_local_file(self):
        with ExitStack() as stack:
            root, create, app = self.scenario(stack)
            self.click(app, "Ajouter un chant")
            app.text_input[0].set_value("Nouveau")
            app.text_area[0].set_value("Mes paroles")
            create.side_effect = ValueError("GitHub est injoignable.")
            self.click(app, "Enregistrer")
            self.assertFalse(app.exception)
            self.assertEqual(app.text_area[0].value, "Mes paroles")
            self.assertTrue(app.error)
            self.assertFalse((root / "chants/nouveau.md").exists())
            self.click(app, "Annuler")
            self.assertFalse(app.text_area)
            self.click(app, "Ajouter un chant")
            self.assertEqual(app.text_input[0].value, "")
            self.assertEqual(app.text_area[0].value, "")

    def test_local_duplicate_and_invalid_lyrics_do_not_send(self):
        with ExitStack() as stack:
            root, create, app = self.scenario(stack)
            (root / "chants").mkdir()
            existing = root / "chants/ete.md"
            existing.write_text("Anciennes paroles", encoding="utf-8")
            self.click(app, "Ajouter un chant")
            app.text_input[0].set_value("Été")
            app.text_area[0].set_value("Nouvelles paroles")
            self.click(app, "Enregistrer")
            self.assertTrue(app.error)
            create.assert_not_called()
            self.assertEqual(existing.read_text(encoding="utf-8"), "Anciennes paroles")
            app.text_input[0].set_value("Autre")
            for invalid in ("", "<!-- refrain -->", "<!-- ordre: C2 -->\nCouplet"):
                app.text_area[0].set_value(invalid)
                self.click(app, "Enregistrer")
                self.assertFalse(app.exception)
                self.assertTrue(app.error)
                create.assert_not_called()

    def test_missing_configuration_disables_add_even_in_empty_catalog(self):
        with ExitStack() as stack:
            _, create, app = self.scenario(stack, configured=False)
            self.assertTrue(next(button for button in app.button if button.label == "Ajouter un chant").disabled)
            create.assert_not_called()

    def test_local_failure_after_remote_success_still_reports_success(self):
        with ExitStack() as stack:
            root, create, app = self.scenario(stack)
            self.click(app, "Ajouter un chant")
            app.text_input[0].set_value("Nouveau")
            app.text_area[0].set_value("Paroles")
            with patch("pathlib.Path.mkdir", side_effect=OSError("lecture seule")):
                self.click(app, "Enregistrer")
            self.assertFalse(app.exception)
            create.assert_called_once()
            self.assertTrue(app.success)
            self.assertTrue(app.warning)
            self.assertFalse((root / "chants/nouveau.md").exists())


if __name__ == "__main__":
    unittest.main()
