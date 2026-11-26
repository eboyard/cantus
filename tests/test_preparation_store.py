from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from scripts.github_publish import GitHubPublishError
from scripts.preparation_store import decode_preparation, encode_preparation, load_preparation, save_preparation
from scripts.aelf import parse_aelf_response
from scripts.liturgical_texts import reading_documents


SONG = ("<!-- titre: Chant -->\n<!-- refrain -->\nRefrain\n---\n"
        "<!-- couplet: C1 -->\nPremier\n---\n<!-- couplet: C2 -->\nDeuxième\n---\n"
        "<!-- couplet: C3 -->\nTroisième")


class PreparationStoreTests(unittest.TestCase):
    def test_roundtrip_preserves_duplicates_order_moments_and_all_verse_states_without_secrets(self):
        state = {
            "celebration_title": "Messe à Boussy", "celebration_date": date(2026, 11, 29),
            "song_order": ["chants/a.md", "chants/b.md", "chants/a.md"],
            "song_moments": ["Chant d’entrée", "", "Envoi"],
            "song_verses": [None, [], ["C1", "C3"]],
            "pages_publish_password": "secret-code", "generated_song_sheet": b"export",
        }
        raw = encode_preparation(state)
        restored = decode_preparation(raw)
        self.assertNotIn(b"secret-code", raw)
        self.assertNotIn(b"generated_song_sheet", raw)
        for key in ("celebration_title", "celebration_date", "song_order", "song_moments", "song_verses"):
            self.assertEqual(restored[key], state[key])

    def test_export_uses_indented_ordered_song_objects(self):
        state = {
            "song_order": ["chants/été.md", "chants/b.md", "chants/été.md"],
            "song_moments": ["Chant d’entrée", "", "Envoi"],
            "song_verses": [None, [], ["C3", "C1"]],
        }
        raw = encode_preparation(state)
        document = json.loads(raw)
        self.assertEqual(document, {"version": 2, "preparation": {"songs": [
            {"path": "chants/été.md", "moment": "Chant d’entrée", "verses": None},
            {"path": "chants/b.md", "moment": "", "verses": []},
            {"path": "chants/été.md", "moment": "Envoi", "verses": ["C3", "C1"]},
        ]}})
        self.assertEqual(raw.decode("utf-8"), json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        self.assertEqual(state["song_order"], ["chants/été.md", "chants/b.md", "chants/été.md"])

    def test_legacy_backup_can_be_imported_and_exported_in_new_format(self):
        state = {"celebration_title": "Ancienne préparation", "song_order": ["chants/a.md"],
                 "song_moments": ["Envoi"], "song_verses": [["C2"]]}
        restored = decode_preparation(json.dumps({"version": 1, "preparation": state}).encode("utf-8"))
        self.assertEqual(restored, state)
        self.assertEqual(decode_preparation(encode_preparation(restored)), state)

    def test_invalid_song_objects_are_rejected(self):
        valid = {"path": "chants/a.md", "moment": "Envoi", "verses": ["C1"]}
        for songs in ({}, [None], ["chants/a.md"], [{}], [{**valid, "extra": True}],
                      [{**valid, "path": ""}], [{**valid, "moment": "inconnu"}],
                      [{**valid, "verses": "C1"}], [{**valid, "verses": [1]}],
                      [{**valid, "verses": ["bad"]}], [valid] * 501):
            with self.subTest(songs=songs), self.assertRaises(ValueError):
                decode_preparation(json.dumps({"version": 2, "preparation": {"songs": songs}}).encode("utf-8"))
        with self.assertRaises(ValueError):
            decode_preparation(b'{"version":2,"preparation":{"songs":[],"song_order":[]}}')

    def test_failed_atomic_replace_preserves_previous_complete_draft(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            identifier = "a" * 64
            old = encode_preparation({"celebration_title": "Avant"})
            save_preparation(root, identifier, old)
            with patch("scripts.preparation_store.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    save_preparation(root, identifier, encode_preparation({"celebration_title": "Après"}))
            self.assertEqual(load_preparation(root, identifier)["celebration_title"], "Avant")
            self.assertEqual(len(list(root.iterdir())), 1)
            with self.assertRaises(ValueError):
                load_preparation(root, "../other")

    def test_invalid_import_is_rejected(self):
        for raw in (b"broken", b'{}', b'{"version":3,"preparation":{}}',
                    b'{"version":1,"preparation":{"song_order":["a"],"song_moments":[],"song_verses":[]}}',
                    b'{"version":1,"preparation":{"token":"secret"}}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decode_preparation(raw)


class PreparationRecoveryTests(unittest.TestCase):
    @staticmethod
    def click(app, label):
        next(button for button in app.button if button.label == label).click().run()
        if app.exception:
            raise AssertionError(app.exception)

    @staticmethod
    def start(identifier=None):
        app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20)
        if identifier:
            app.query_params["preparation"] = identifier
        return app

    def test_renamed_psautier_path_is_migrated_in_existing_session_and_saved(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chants").mkdir()
            (root / "chants/psaume_100.md").write_text(SONG, encoding="utf-8")
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"):
                app = self.start()
                app.session_state["preparation_initialized"] = True
                app.session_state["preparation_identifier"] = "a" * 64
                app.session_state["song_order"] = ["chants/psautier_100.md"]
                app.session_state["song_moments"] = ["Psaume"]
                app.session_state["song_verses"] = [["C2"]]
                app.run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["song_order"], ["chants/psaume_100.md"])
                self.assertEqual(app.session_state["song_moments"], ["Psaume"])
                self.assertEqual(app.session_state["song_verses"], [["C2"]])
                saved = load_preparation(root / ".cantus-drafts", "a" * 64)
                self.assertEqual(saved["song_order"], ["chants/psaume_100.md"])

    def test_renamed_psautier_path_is_migrated_when_loading_saved_draft(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chants").mkdir()
            (root / "chants/psaume_100.md").write_text(SONG, encoding="utf-8")
            identifier = "b" * 64
            save_preparation(root / ".cantus-drafts", identifier, encode_preparation({
                "song_order": ["chants/psautier_100.md"],
                "song_moments": ["Psaume"],
                "song_verses": [["C2"]],
            }))
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"):
                app = self.start(identifier).run()
                self.assertFalse(app.exception)
                self.assertEqual(app.session_state["song_order"], ["chants/psaume_100.md"])
                self.assertEqual(load_preparation(root / ".cantus-drafts", identifier)["song_order"],
                                 ["chants/psaume_100.md"])

    def test_missing_song_path_shows_recovery_message_instead_of_crashing(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chants").mkdir()
            (root / "chants/a.md").write_text(SONG, encoding="utf-8")
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"):
                app = self.start()
                app.session_state["preparation_initialized"] = True
                app.session_state["preparation_identifier"] = "c" * 64
                app.session_state["song_order"] = ["chants/missing.md"]
                app.session_state["song_moments"] = ["Envoi"]
                app.session_state["song_verses"] = [["C1"]]
                app.run()
                self.assertFalse(app.exception)
                self.assertTrue(any("Chants absents du catalogue" in error.value for error in app.error))
                self.assertEqual(app.session_state["song_order"], ["chants/missing.md"])

    def test_existing_sheet_sources_and_json_upload_callback(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chants").mkdir()
            (root / "chants/a.md").write_text(SONG, encoding="utf-8")
            # AppTest ne permet pas de téléverser un fichier : reproduire son
            # callback avant le rendu, comme le fait Streamlit.
            script = (
                "import streamlit as st\n"
                "from io import BytesIO\n"
                "from app import show_preparation, restore_preparation_backup\n"
                "if 'candidate' in st.session_state:\n"
                "    st.session_state.preparation_upload = BytesIO(st.session_state.pop('candidate'))\n"
                "    restore_preparation_backup()\n"
                "    del st.session_state.preparation_upload\n"
                "show_preparation()\n"
            )
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"), \
                    patch("app.published_sheets") as network:
                app = AppTest.from_string(script, default_timeout=20).run()
                self.assertFalse(app.exception)
                self.assertEqual(len(app.selectbox(key="existing_sheet_choice").options), 0)
                self.assertEqual(len(app.get("file_uploader")), 0)
                identifier = app.session_state["preparation_identifier"]
                app.radio(key="existing_sheet_source").set_value("Un fichier JSON sauvegardé").run()
                self.assertFalse(app.exception)
                self.assertEqual(len(app.get("file_uploader")), 1)
                self.assertFalse(any(box.key == "existing_sheet_choice" for box in app.selectbox))
                imported = {
                    "celebration_title": "Feuille sauvegardée", "celebration_date": date(2026, 11, 29),
                    "song_order": ["chants/a.md", "chants/a.md"],
                    "song_moments": ["Communion", "Envoi"], "song_verses": [[], ["C1", "C3"]],
                }
                app.session_state["candidate"] = encode_preparation(imported)
                app.run()
                self.assertFalse(app.exception)
                self.assertTrue(app.success)
                restored_identifier = app.session_state["preparation_identifier"]
                self.assertNotEqual(restored_identifier, identifier)
                for key, value in imported.items():
                    self.assertEqual(app.session_state[key], value)
                    self.assertEqual(load_preparation(root / ".cantus-drafts", restored_identifier)[key], value)
                for invalid in (b"broken", encode_preparation({**imported, "song_order": ["missing", "chants/a.md"]})):
                    app.session_state["candidate"] = invalid
                    app.run()
                    self.assertFalse(app.exception)
                    self.assertTrue(app.error)
                    self.assertEqual(app.session_state["preparation_identifier"], restored_identifier)
                    for key, value in imported.items():
                        self.assertEqual(app.session_state[key], value)
                app.radio(key="existing_sheet_source").set_value("Une feuille publiée").run()
                self.assertFalse(app.exception)
                self.assertFalse(app.error)
                self.assertEqual(app.session_state["song_order"], imported["song_order"])
                self.assertEqual(len(app.get("file_uploader")), 0)
                network.assert_not_called()

    def test_failed_publication_and_new_session_keep_entire_preparation(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chants").mkdir()
            (root / "chants/a.md").write_text(SONG, encoding="utf-8")
            (root / "chants/b.md").write_text(SONG.replace("Chant", "Autre"), encoding="utf-8")
            settings = {"token": "token", "publish_password": "code", "repository": "owner/repo", "branch": "main"}
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"), \
                    patch("app.github_setting", side_effect=lambda key, default="": settings.get(key, default)), \
                    patch("app.publish_sheet") as publish:
                app = self.start()
                app.session_state["song_order"] = ["chants/a.md", "chants/b.md", "chants/a.md"]
                app.session_state["song_moments"] = ["Chant d’entrée", "Communion", "Envoi"]
                app.session_state["song_verses"] = [["C1", "C3"], [], ["C2"]]
                app.run()
                self.assertFalse(app.exception)
                app.text_input(key="celebration_title").set_value("Préparation de Gilles").run()
                # Changer une rubrique plus bas et déplacer la première occurrence.
                app.selectbox(key="sheet_moment_2").select("Offertoire")
                app.checkbox(key="sheet_verses_2_C3").check()
                app.button(key="down-0").click().run()
                self.assertFalse(app.exception)
                expected = {key: deepcopy(app.session_state[key]) for key in
                            ("song_order", "song_moments", "song_verses", "celebration_title", "celebration_date")}
                self.assertEqual(expected["song_order"], ["chants/b.md", "chants/a.md", "chants/a.md"])
                self.assertEqual(expected["song_moments"], ["Communion", "Chant d’entrée", "Offertoire"])
                self.assertEqual(expected["song_verses"], [[], ["C1", "C3"], ["C2", "C3"]])
                self.click(app, "Créer la feuille de chants")
                self.click(app, "Préparer pour GitHub Pages")
                self.click(app, "Publier sur GitHub Pages")
                publish.assert_not_called()  # Code absent : aucune tentative distante.
                app.text_input(key="pages_publish_password").set_value("code")
                for error in (GitHubPublishError("GitHub est injoignable"), TimeoutError("timeout"), RuntimeError("unexpected")):
                    publish.side_effect = error
                    self.click(app, "Publier sur GitHub Pages")
                    self.assertTrue(any("préparation est conservée" in item.value for item in app.error))
                    for key, value in expected.items():
                        self.assertEqual(app.session_state[key], value)
                identifier = app.session_state["preparation_identifier"]
                disk = load_preparation(root / ".cantus-drafts", identifier)
                for key, value in expected.items():
                    self.assertEqual(disk[key], value)
                reopened = self.start(identifier).run()
                self.assertFalse(reopened.exception)
                for key, value in expected.items():
                    self.assertEqual(reopened.session_state[key], value)
                self.assertNotIn("pages_publish_password", disk)
                publish.side_effect = None
                publish.return_value = "https://github.com/owner/repo/commit/test"
                self.click(reopened, "Créer la feuille de chants")
                self.click(reopened, "Préparer pour GitHub Pages")
                reopened.text_input(key="pages_publish_password").set_value("code")
                self.click(reopened, "Publier sur GitHub Pages")
                self.assertTrue(reopened.success)
                self.assertEqual(load_preparation(root / ".cantus-drafts", identifier)["song_order"], expected["song_order"])
                # Un visiteur sans lien de reprise reçoit un brouillon distinct.
                other = self.start().run()
                self.assertFalse(other.exception)
                self.assertEqual(other.session_state["song_order"], [])
                self.assertNotEqual(other.query_params["preparation"], app.query_params["preparation"])

    def test_corrupt_draft_is_never_replaced_with_empty_state(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            drafts = root / ".cantus-drafts"
            drafts.mkdir()
            identifier = "b" * 64
            path = drafts / f"{identifier}.json"
            path.write_bytes(b"corrupt")
            (root / "chants").mkdir()
            (root / "chants/a.md").write_text(SONG, encoding="utf-8")
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"):
                app = self.start(identifier).run()
                self.assertFalse(app.exception)
                self.assertTrue(app.warning)
                self.assertEqual(path.read_bytes(), b"corrupt")

    def test_recovery_rebuilds_aelf_and_readings_without_network(self):
        payload = json.loads((Path(__file__).parent / "fixtures/aelf_2026_11_15.json").read_text(encoding="utf-8"))
        payload["messes"][0]["lectures"].insert(0, {"type": "lecture_1", "intro_lue": "Lecture du livre des Proverbes"})
        mass, = parse_aelf_response(payload, date(2026, 11, 15))
        readings = reading_documents(mass.markdown)
        self.assertTrue(readings)
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chants").mkdir()
            (root / "chants/a.md").write_text(SONG, encoding="utf-8")
            identifier = "c" * 64
            order = ["chants/a.md", mass.key, *readings]
            original = {
                "song_order": order, "song_moments": ["Chant d’entrée", "Psaume", *[""] * len(readings)],
                "song_verses": [None] * len(order), "celebration_date": mass.day,
                "aelf_psalms": {mass.key: mass.markdown}, "reading_texts": readings,
                "selected_aelf_context": mass.markdown,
            }
            save_preparation(root / ".cantus-drafts", identifier, encode_preparation(original))
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"), \
                    patch("app.load_aelf_masses") as network:
                restored = self.start(identifier).run()
                self.assertFalse(restored.exception)
                self.assertEqual(restored.session_state["song_order"], order)
                self.assertEqual(restored.session_state["aelf_psalms"], original["aelf_psalms"])
                self.assertEqual(restored.session_state["reading_texts"], readings)
                self.assertEqual(restored.session_state["selected_aelf_context"], mass.markdown)
                network.assert_not_called()
                self.click(restored, "Créer la feuille de chants")
                self.assertIn("generated_song_sheet", restored.session_state)

    def test_disk_failure_warns_but_keeps_selection_and_download_available(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chants").mkdir()
            (root / "chants/a.md").write_text(SONG, encoding="utf-8")
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"), \
                    patch("app.save_preparation", side_effect=OSError("disk full")):
                app = self.start()
                app.session_state["song_order"] = ["chants/a.md"]
                app.session_state["song_moments"] = ["Communion"]
                app.session_state["song_verses"] = [["C1", "C3"]]
                app.run()
                self.assertFalse(app.exception)
                self.assertTrue(app.warning)
                self.assertEqual(app.session_state["song_verses"], [["C1", "C3"]])
                self.assertTrue(any(button.label == "Télécharger la préparation (.cantus.json)"
                                    for button in app.get("download_button")))

    def test_import_validates_before_replacing_current_selection(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "chants").mkdir()
            (root / "chants/a.md").write_text(SONG, encoding="utf-8")
            script = (
                "import streamlit as st\n"
                "from app import show_preparation, apply_preparation\n"
                "from scripts.preparation_store import decode_preparation\n"
                "if 'candidate' in st.session_state:\n"
                "    try:\n"
                "        apply_preparation(decode_preparation(st.session_state.pop('candidate')))\n"
                "    except ValueError as error:\n"
                "        st.session_state.import_error = str(error)\n"
                "show_preparation()\n"
            )
            with patch("app.ROOT", root), patch("app.SONGS_DIR", root / "chants"):
                app = AppTest.from_string(script, default_timeout=20)
                original = {"song_order": ["chants/a.md"], "song_moments": ["Envoi"], "song_verses": [["C3"]]}
                for key, value in original.items():
                    app.session_state[key] = value
                app.run()
                invalid = {**original, "song_order": ["chants/missing.md"]}
                app.session_state["candidate"] = encode_preparation(invalid)
                app.run()
                self.assertFalse(app.exception)
                self.assertIn("manque", app.session_state["import_error"])
                for key, value in original.items():
                    self.assertEqual(app.session_state[key], value)
                imported = {"song_order": ["chants/a.md", "chants/a.md"],
                            "song_moments": ["Communion", "Envoi"], "song_verses": [[], ["C1", "C3"]]}
                app.session_state["candidate"] = encode_preparation(imported)
                app.run()
                self.assertFalse(app.exception)
                for key, value in imported.items():
                    self.assertEqual(app.session_state[key], value)


if __name__ == "__main__":
    unittest.main()
