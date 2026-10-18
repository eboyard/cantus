import base64
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from streamlit.testing.v1 import AppTest

from scripts.sheet_library import ExistingSheet, local_sheets, published_sheets, read_existing_sheet, songs_from_contents
from scripts.song_sheet import create_song_sheet


def contents(*titles):
    return '<nav id="sommaire"><ol>' + ''.join(
        f'<li><a href="#chant-{i}">{title}</a></li>' for i, title in enumerate(titles, 1)
    ) + '</ol></nav>'


def response(data):
    return BytesIO(json.dumps(data).encode())


class SheetLibraryTests(unittest.TestCase):
    def test_old_contents_match_titles_with_accents_spacing_and_duplicates(self):
        catalog = {"a": ("Ô Marie, prends nos prières", Path("a.md")), "b": ("Agnus Dei", Path("b.md"))}
        html = contents("Agnus Dei", "O Marie,\nprends nos prières", "Agnus Dei")
        html += '<section><a href="#chant-1">Retour</a></section>'
        self.assertEqual(songs_from_contents(html, catalog), ["b", "a", "b"])

    def test_unknown_ambiguous_or_missing_contents_do_not_silently_omit_songs(self):
        catalog = {"a": ("Même titre", Path("a.md")), "b": ("Même titre", Path("b.md"))}
        with self.assertRaisesRegex(ValueError, "plusieurs correspondances"):
            songs_from_contents(contents("Même titre"), catalog)
        with self.assertRaisesRegex(ValueError, "absent du carnet"):
            songs_from_contents(contents("Inconnu"), catalog)
        with self.assertRaisesRegex(ValueError, "sommaire"):
            songs_from_contents("<h1>Agnus Dei</h1>", catalog)

    def test_new_sheet_uses_source_keys_even_after_title_change(self):
        root = Path(__file__).resolve().parents[1]
        song = root / "chants/agnus_dei.md"
        html = create_song_sheet("Messe", [("Ancien titre", song)]).decode()
        self.assertIn('data-song-key="chants/agnus_dei.md"', html)
        self.assertEqual(songs_from_contents(html, {"chants/agnus_dei.md": ("Nouveau titre", song)}), ["chants/agnus_dei.md"])

    def test_local_listing_excludes_parish_indexes_and_invalid_dates(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for path in ("paroisse/index.html", "paroisse/2026-10-17/index.html", "paroisse/2026-11-07/index.html", "paroisse/2026-02-30/index.html"):
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(contents("Chant"), encoding="utf-8")
            sheets = local_sheets(root)
            self.assertEqual([sheet.path for sheet in sheets], ["paroisse/2026-11-07/index.html", "paroisse/2026-10-17/index.html"])
            self.assertIn("07/11/2026", sheets[0].label)
            self.assertEqual(read_existing_sheet(sheets[0], root, "", ""), contents("Chant"))
            with self.assertRaises(ValueError):
                read_existing_sheet(ExistingSheet("../ailleurs/index.html"), root, "", "")

    def test_remote_listing_and_download_use_selected_branch_and_blob_snapshot(self):
        sha = "a" * 40
        tree = {"truncated": False, "tree": [
            {"path": "docs/boussy-saint-antoine/2026-10-18/index.html", "type": "blob", "mode": "100644", "sha": sha},
            {"path": "docs/boussy-saint-antoine/index.html", "type": "blob", "mode": "100644", "sha": sha},
        ]}
        responses = [response({"object": {"sha": "b" * 40}}), response({"tree": {"sha": "c" * 40}}), response(tree),
                     response({"encoding": "base64", "content": base64.b64encode(contents("Agnus Dei").encode()).decode()})]
        with patch("scripts.github_publish.urlopen", side_effect=responses) as send:
            sheets = published_sheets("private-token", "owner/repo", "feuilles")
            self.assertEqual(len(sheets), 1)
            self.assertEqual(read_existing_sheet(sheets[0], Path("docs"), "private-token", "owner/repo"), contents("Agnus Dei"))
            self.assertTrue(send.call_args_list[0].args[0].full_url.endswith("/git/ref/heads/feuilles"))
            self.assertTrue(send.call_args.args[0].full_url.endswith(f"/git/blobs/{sha}"))

    def test_remote_failure_is_readable_without_disclosing_token(self):
        with patch("scripts.github_publish.urlopen", side_effect=HTTPError("https://api.github.com", 403, "private-token", {}, None)):
            with self.assertRaisesRegex(ValueError, "Impossible de lire") as caught:
                published_sheets("private-token", "owner/repo", "main")
            self.assertNotIn("private-token", str(caught.exception))

    def test_public_repository_has_no_empty_auth_header_and_truncated_list_is_rejected(self):
        responses = [response({"object": {"sha": "b" * 40}}), response({"tree": {"sha": "c" * 40}}),
                     response({"truncated": True, "tree": []})]
        with patch("scripts.github_publish.urlopen", side_effect=responses) as send:
            with self.assertRaisesRegex(ValueError, "liste complète"):
                published_sheets("", "owner/repo", "main")
            for call in send.call_args_list:
                self.assertIsNone(call.args[0].get_header("Authorization"))

    def test_ui_selection_replaces_order_once_and_failed_import_preserves_it(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            song = root / "chant.md"
            song.write_text("Paroles", encoding="utf-8")
            catalog = {"a": ("Chant A", song), "b": ("Chant B", song)}
            source = root / "docs/paroisse/2026-10-18/index.html"
            source.parent.mkdir(parents=True)
            source.write_text(contents("Chant B", "Chant A", "Chant B"), encoding="utf-8")
            invalid = root / "docs/paroisse/2026-10-19/index.html"
            invalid.parent.mkdir(parents=True)
            invalid.write_text(contents("Introuvable"), encoding="utf-8")
            with patch("app.ROOT", root), patch("app.song_catalog", return_value=catalog):
                app = AppTest.from_string("from app import main\nmain()")
                app.session_state["song_order"] = ["a"]
                app.run()
                app.selectbox(key="existing_sheet_choice").select("paroisse/2026-10-18/index.html").run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["song_order"], ["b", "a", "b"])
                next(button for button in app.button if button.label == "Ajouter le chant").click().run()
                self.assertEqual(len(app.session_state["song_order"]), 4)
                previous = list(app.session_state["song_order"])
                app.selectbox(key="existing_sheet_choice").select("paroisse/2026-10-19/index.html").run()
                self.assertEqual(app.session_state["song_order"], previous)
                self.assertIn("Introuvable", app.error[0].value)
                self.assertFalse(app.exception)

    def test_ui_refresh_makes_remote_only_sheet_available(self):
        sheet = ExistingSheet("quincy-sous-senart/2026-10-25/index.html", "a" * 40)
        with patch("app.published_sheets", return_value=[sheet]), patch("app.read_existing_sheet", return_value=contents("Agnus Dei")):
            app = AppTest.from_string("from app import main\nmain()").run()
            app.button(key="refresh_existing_sheets").click().run()
            app.selectbox(key="existing_sheet_choice").select(sheet.path).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["song_order"], ["chants/agnus_dei.md"])


if __name__ == "__main__":
    unittest.main()
