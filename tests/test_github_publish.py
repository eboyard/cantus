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


PARENT = "b" * 40
TREE = "c" * 40
NEW_TREE = "d" * 40
SHA = "a" * 40


def snapshot(paths=(), truncated=False):
    return [
        response({"object": {"sha": PARENT}}),
        response({"tree": {"sha": TREE}}),
        response({"truncated": truncated, "tree": [
            {"path": path, "type": "blob", "mode": "100644", "sha": "e" * 40} for path in paths
        ]}),
    ]


def publication():
    return [response({"sha": NEW_TREE}), response({"sha": SHA}), response({"object": {"sha": SHA}})]


def response(value):
    return BytesIO(json.dumps(value).encode("utf-8"))


def http_error(status):
    return HTTPError("https://api.github.com/test", status, "secret-response-must-not-appear", {}, None)


class GitHubPublishTests(unittest.TestCase):
    def setUp(self):
        self.export = prepare_pages_export("<html>Grâce</html>".encode("utf-8"), "Saint-Pierre", date(2026, 10, 18), "https://eboyard.github.io/cantus")

    def test_sheet_and_parish_index_are_published_in_one_commit(self):
        paths = ["docs/saint-pierre/2026-10-11/index.html", "docs/saint-pierre/2026-10-25/index.html",
                 "docs/saint-paul/2026-09-01/index.html", "docs/saint-pierre/2026-02-30/index.html"]
        with patch("scripts.github_publish.urlopen", side_effect=snapshot(paths) + publication()) as send:
            url = publish_sheet(self.export, "test-token")
        self.assertEqual(url, "https://github.com/eboyard/cantus/commit/" + "a" * 40)
        requests = [call.args[0] for call in send.call_args_list]
        self.assertEqual([r.get_method() for r in requests], ["GET", "GET", "GET", "POST", "POST", "PATCH"])
        self.assertTrue(requests[0].full_url.endswith("/git/ref/heads/main"))
        payload = json.loads(requests[3].data)
        self.assertEqual(payload["base_tree"], TREE)
        files = {item["path"]: item["content"] for item in payload["tree"]}
        self.assertEqual(set(files), {"docs/saint-pierre/2026-10-18/index.html", "docs/saint-pierre/index.html", "docs/.nojekyll"})
        self.assertEqual(files["docs/saint-pierre/2026-10-18/index.html"], self.export.document.decode())
        index = files["docs/saint-pierre/index.html"]
        self.assertIn("Saint-Pierre", index)
        self.assertLess(index.index('href="2026-10-25/"'), index.index('href="2026-10-18/"'))
        self.assertLess(index.index('href="2026-10-18/"'), index.index('href="2026-10-11/"'))
        self.assertNotIn("2026-09-01", index)
        self.assertNotIn("2026-02-30", index)
        self.assertEqual(json.loads(requests[4].data)["parents"], [PARENT])
        self.assertEqual(json.loads(requests[4].data)["tree"], NEW_TREE)
        self.assertEqual(json.loads(requests[5].data), {"sha": SHA, "force": False})
        for request in requests:
            self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
            self.assertNotIn("test-token", request.full_url)
            self.assertNotIn("test-token", (request.data or b"").decode())

    def test_existing_file_requires_explicit_replacement_without_duplicate(self):
        existing = ["docs/saint-pierre/2026-10-18/index.html"]
        with patch("scripts.github_publish.urlopen", side_effect=snapshot(existing)) as send:
            with self.assertRaisesRegex(GitHubPublishError, "existe déjà"):
                publish_sheet(self.export, "token")
            self.assertEqual(send.call_count, 3)
        with patch("scripts.github_publish.urlopen", side_effect=snapshot(existing) + publication()) as send:
            publish_sheet(self.export, "token", replace=True)
            index = json.loads(send.call_args_list[3].args[0].data)["tree"][1]["content"]
            self.assertEqual(index.count('href="2026-10-18/"'), 1)

    def test_concurrent_publication_does_not_force_branch_or_claim_success(self):
        with patch("scripts.github_publish.urlopen", side_effect=snapshot() + publication()[:2] + [http_error(422)]) as send:
            with self.assertRaises(GitHubPublishError):
                publish_sheet(self.export, "token")
            self.assertFalse(json.loads(send.call_args.args[0].data)["force"])

    def test_truncated_listing_never_overwrites_index(self):
        with patch("scripts.github_publish.urlopen", side_effect=snapshot(truncated=True)) as send:
            with self.assertRaisesRegex(GitHubPublishError, "liste complète"):
                publish_sheet(self.export, "token")
            self.assertEqual(send.call_count, 3)

    def test_api_errors_are_readable_without_disclosing_responses(self):
        for status in (401, 403, 404, 409, 422, 500):
            with self.subTest(status=status), patch("scripts.github_publish.urlopen", side_effect=[http_error(status)]):
                with self.assertRaises(GitHubPublishError) as caught:
                    publish_sheet(self.export, "private-token")
                self.assertNotIn("private-token", str(caught.exception))
                self.assertNotIn("secret-response", str(caught.exception))
        with patch("scripts.github_publish.urlopen", side_effect=URLError("private-token")):
            with self.assertRaisesRegex(GitHubPublishError, "injoignable"):
                publish_sheet(self.export, "private-token")

    def test_unexpected_responses_do_not_claim_success(self):
        for result in ({}, {"sha": None}, {"sha": "invalid"}):
            with self.subTest(result=result), patch("scripts.github_publish.urlopen", side_effect=snapshot() + [response({"sha": NEW_TREE}), response(result)]):
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
                index_button = next(button for button in app.get("link_button") if button.proto.label == "Toutes les feuilles de la paroisse")
                self.assertEqual(index_button.proto.url, "https://eboyard.github.io/cantus/boussy-saint-antoine/")
                app.selectbox(key="pages_parish").select("Quincy-sous-Sénart").run()
                self.assertEqual(len(app.get("link_button")), 0)


if __name__ == "__main__":
    unittest.main()
