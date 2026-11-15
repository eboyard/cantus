from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class SongAuthorizationTests(unittest.TestCase):
    @staticmethod
    def click(app, label):
        return next(button for button in app.button if button.label == label).click().run()

    def scenario(self, stack, token="same-github-token", password="Même code Pages"):
        root = Path(stack.enter_context(TemporaryDirectory()))
        (root / "chants").mkdir()
        path = root / "chants/existant.md"
        original = "<!-- titre: Existant -->\nAnciennes paroles"
        path.write_text(original, encoding="utf-8")
        settings = {"token": token, "publish_password": password, "repository": "owner/repo", "branch": "main"}
        stack.enter_context(patch("app.ROOT", root))
        stack.enter_context(patch("app.SONGS_DIR", root / "chants"))
        stack.enter_context(patch("app.github_setting", side_effect=lambda name, default="": settings.get(name, default)))
        stack.enter_context(patch("app.load_song", return_value=(original, "a" * 40)))
        create = stack.enter_context(patch("app.create_song", return_value="https://github.com/commit"))
        save = stack.enter_context(patch("app.save_song", return_value="https://github.com/commit"))
        app = AppTest.from_string("from app import show_lyrics\nshow_lyrics()").run()
        return app, root, settings, create, save

    def test_empty_or_wrong_code_blocks_both_writes_and_correct_code_uses_same_token(self):
        for creation in (True, False):
            with self.subTest(creation=creation), ExitStack() as stack:
                app, root, _, create, save = self.scenario(stack)
                if creation:
                    self.click(app, "Ajouter un chant")
                    app.text_input(key="song_create_title").set_value("Nouveau")
                    lyrics_key, code_key = "song_create_lyrics", "song_create_password"
                else:
                    app.selectbox(key="lyrics_song").select("chants/existant.md").run()
                    self.click(app, "Modifier")
                    lyrics_key, code_key = "song_edit_markdown", "song_edit_password"
                document = "<!-- titre: Nouveau -->\nNouvelles paroles" if not creation else "Nouvelles paroles"
                app.text_area(key=lyrics_key).set_value(document)
                for code in ("", "incorrect"):
                    app.text_input(key=code_key).set_value(code)
                    self.click(app, "Enregistrer")
                    self.assertFalse(app.exception)
                    self.assertIn("code de publication est incorrect", app.error[0].value)
                    self.assertEqual(app.text_area(key=lyrics_key).value, document)
                    create.assert_not_called()
                    save.assert_not_called()
                    self.assertFalse((root / "chants/nouveau.md").exists())
                    self.assertIn("Anciennes", (root / "chants/existant.md").read_text(encoding="utf-8"))
                app.text_input(key=code_key).set_value("Même code Pages")
                self.click(app, "Enregistrer")
                self.assertFalse(app.exception)
                writer = create if creation else save
                writer.assert_called_once()
                self.assertEqual(writer.call_args.args[0], "same-github-token")

    def test_missing_token_or_password_disables_both_actions(self):
        for token, password in (("", "configured"), ("configured", "")):
            with self.subTest(token=bool(token)), ExitStack() as stack:
                app, _, _, create, save = self.scenario(stack, token, password)
                self.assertTrue(next(button for button in app.button if button.label == "Ajouter un chant").disabled)
                app.selectbox(key="lyrics_song").select("chants/existant.md").run()
                self.assertTrue(next(button for button in app.button if button.label == "Modifier").disabled)
                create.assert_not_called()
                save.assert_not_called()

    def test_changing_password_during_edit_blocks_old_code(self):
        with ExitStack() as stack:
            app, _, settings, create, save = self.scenario(stack)
            app.selectbox(key="lyrics_song").select("chants/existant.md").run()
            self.click(app, "Modifier")
            app.text_area(key="song_edit_markdown").set_value("Nouvelles paroles")
            app.text_input(key="song_edit_password").set_value("Même code Pages")
            settings["publish_password"] = "Nouveau code"
            self.click(app, "Enregistrer")
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            create.assert_not_called()
            save.assert_not_called()

    def test_missing_server_configuration_cannot_authorize_empty_code(self):
        from app import check_song_publication_code
        for token, password in (("token", ""), ("", "code")):
            with self.subTest(token=bool(token)), self.assertRaises(ValueError):
                check_song_publication_code(password, password, token)


if __name__ == "__main__":
    unittest.main()
