import base64
from datetime import date
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from streamlit.testing.v1 import AppTest

from scripts.github_pages import prepare_pages_export
from scripts.github_publish import GitHubPublishError, publish_sheet


COMMIT = {"commit": {"sha": "a" * 40}}


def response(value):
    return BytesIO(json.dumps(value).encode("utf-8"))


def http_error(status):
    return HTTPError("https://api.github.com/test", status, "secret-response-must-not-appear", {}, None)


class GitHubPublishTests(unittest.TestCase):
    def setUp(self):
        self.export = prepare_pages_export("<html>Grâce</html>".encode("utf-8"), "Saint-Pierre", date(2026, 10, 18), "https://eboyard.github.io/cantus")

    def test_new_file_uses_docs_main_and_only_publishes_the_html(self):
        with patch("scripts.github_publish.urlopen", side_effect=[http_error(404), response(COMMIT)]) as send:
            url = publish_sheet(self.export, "test-token")
        self.assertEqual(url, "https://github.com/eboyard/cantus/commit/" + "a" * 40)
        self.assertEqual(send.call_count, 2)
        get, put = [call.args[0] for call in send.call_args_list]
        self.assertTrue(get.full_url.endswith("/contents/docs/saint-pierre/2026-10-18/index.html?ref=main"))
        self.assertEqual(put.get_method(), "PUT")
        self.assertEqual(put.get_header("Authorization"), "Bearer test-token")
        payload = json.loads(put.data)
        self.assertEqual(base64.b64decode(payload["content"]), self.export.document)
        self.assertEqual(payload["branch"], "main")
        self.assertNotIn("sha", payload)
        self.assertNotIn("test-token", put.full_url)
        self.assertNotIn("test-token", put.data.decode())

    def test_existing_file_requires_explicit_replacement_and_sends_current_sha(self):
        existing = {"sha": "old-sha", "type": "file"}
        with patch("scripts.github_publish.urlopen", return_value=response(existing)) as send:
            with self.assertRaisesRegex(GitHubPublishError, "existe déjà"):
                publish_sheet(self.export, "token")
            self.assertEqual(send.call_count, 1)
        with patch("scripts.github_publish.urlopen", side_effect=[response(existing), response(COMMIT)]) as send:
            publish_sheet(self.export, "token", replace=True)
            self.assertEqual(json.loads(send.call_args.args[0].data)["sha"], "old-sha")

    def test_api_errors_are_readable_without_disclosing_responses(self):
        for status in (401, 403, 404, 409, 422, 500):
            with self.subTest(status=status), patch("scripts.github_publish.urlopen", side_effect=[http_error(404), http_error(status)]):
                with self.assertRaises(GitHubPublishError) as caught:
                    publish_sheet(self.export, "private-token")
                self.assertNotIn("private-token", str(caught.exception))
                self.assertNotIn("secret-response", str(caught.exception))
        with patch("scripts.github_publish.urlopen", side_effect=URLError("private-token")):
            with self.assertRaisesRegex(GitHubPublishError, "injoignable"):
                publish_sheet(self.export, "private-token")

    def test_unexpected_responses_do_not_claim_success(self):
        for result in ({}, {"commit": None}, {"commit": {"sha": "invalid"}}):
            with self.subTest(result=result), patch("scripts.github_publish.urlopen", side_effect=[http_error(404), response(result)]):
                with self.assertRaisesRegex(GitHubPublishError, "confirmé"):
                    publish_sheet(self.export, "private-token")

    def test_ui_authorizes_publication_with_code_and_handles_success(self):
        with TemporaryDirectory() as directory:
            song = Path(directory) / "chant.md"
            song.write_text("Paroles", encoding="utf-8")
            with patch("app.song_catalog", return_value={"chant": ("Chant", song)}), patch.dict("os.environ", {"GITHUB_TOKEN": "private-token", "SHEET_PUBLISH_PASSWORD": "organisateur"}), patch("app.publish_sheet", return_value="https://github.com/eboyard/cantus/commit/" + "a" * 40) as publish:
                app = AppTest.from_string("from app import main\nmain()")
                app.session_state["song_order"] = ["chant"]
                app.run()
                next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
                app.selectbox(key="pages_parish").select("Boussy-saint-Antoine").run()
                next(button for button in app.button if button.label == "Préparer pour GitHub Pages").click().run()
                next(button for button in app.button if button.label == "Publier sur GitHub Pages").click().run()
                publish.assert_not_called()
                self.assertIn("code de publication", app.error[0].value)
                app.text_input(key="pages_publish_password").set_value("organisateur").run()
                next(button for button in app.button if button.label == "Publier sur GitHub Pages").click().run()
                publish.assert_called_once()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.error), 0)
                self.assertIn("envoyée sur GitHub", app.success[0].value)
                self.assertTrue(any(button.proto.label == "Voir le commit publié" for button in app.get("link_button")))
                app.selectbox(key="pages_parish").select("Quincy-sous-Sénart").run()
                self.assertEqual(len(app.get("link_button")), 0)


if __name__ == "__main__":
    unittest.main()
