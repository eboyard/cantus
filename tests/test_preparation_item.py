from copy import deepcopy
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from scripts.preparation_item import PreparationItem, items_from_columns, move_item, remove_item
from scripts.preparation_store import encode_preparation, decode_preparation, load_preparation
from scripts.sheet_library import moments_from_contents, verses_from_contents


SONG = ("<!-- titre: Chant -->\n<!-- refrain -->\nRefrain\n---\n"
        "<!-- couplet: C1 -->\nPremier\n---\n<!-- couplet: C2 -->\nDeuxième\n---\n"
        "<!-- couplet: C3 -->\nTroisième")


class PreparationItemTests(unittest.TestCase):
    def test_move_and_remove_operate_on_complete_occurrences_including_duplicates(self):
        first = PreparationItem("a", "Même titre", "Chant d’entrée", ["C1"])
        second = PreparationItem("a", "Même titre", "Communion", ["C2", "C3"])
        items = [first, second]
        self.assertNotEqual(first.uid, second.uid)
        move_item(items, first.uid, 1)
        self.assertIs(items[1], first)
        self.assertEqual(items[1].record(), {"path": "a", "moment": "Chant d’entrée", "verses": ["C1"]})
        move_item(items, first.uid, -1)
        self.assertIs(items[0], first)
        remove_item(items, second.uid)
        self.assertEqual(items, [first])
        move_item(items, first.uid, -1)
        move_item(items, "removed", 1)
        self.assertEqual(items, [first])

    def test_legacy_conversion_copies_selections_and_preserves_backup_format(self):
        selected = [["C1"], None]
        items = items_from_columns(["a", "a"], ["Communion", "Envoi"], selected, {"a": ("Titre", None)})
        selected[0].append("C3")
        self.assertEqual(items[0].verses, ["C1"])
        self.assertEqual(items[1].title, "Titre")
        raw = encode_preparation({"preparation_items": items, "celebration_date": date(2026, 11, 29)})
        saved = json.loads(raw)
        self.assertEqual(saved["version"], 2)
        self.assertEqual(saved["preparation"]["songs"], [item.record() for item in items])
        restored = decode_preparation(raw)
        self.assertEqual(restored["song_moments"], ["Communion", "Envoi"])
        self.assertEqual(restored["song_verses"], [["C1"], None])
        with self.assertRaises(ValueError):
            items_from_columns(["a"], [], [None], {})

    def test_widgets_follow_identity_through_moves_edits_removal_exports_and_recovery(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "chants").mkdir()
            path = root / "chants/a.md"
            path.write_text(SONG, encoding="utf-8")
            catalog = {"chants/a.md": ("Chant", path)}
            with patch("app.ROOT", root), patch("app.song_catalog", side_effect=lambda: dict(catalog)):
                script = "from app import show_preparation\nshow_preparation()"
                app = AppTest.from_string(script, default_timeout=20)
                app.session_state["preparation_items"] = [
                    PreparationItem("chants/a.md", "Chant", "Chant d’entrée", ["C1"]),
                    PreparationItem("chants/a.md", "Chant", "Offertoire", ["C2"]),
                    PreparationItem("chants/a.md", "Chant", "Communion", ["C1", "C3"]),
                ]
                app.run()
                self.assertFalse(app.exception)
                first, second, third = app.session_state["preparation_items"]
                identities = [first.uid, second.uid, third.uid]
                # Éditions plus bas dans la page, puis déplacement du premier bloc
                # dans la même interaction : aucun champ ne doit changer d'objet.
                app.selectbox(key=f"sheet_moment_{third.uid}").select("Envoi")
                app.checkbox(key=f"sheet_verses_{third.uid}_C2").check()
                app.button(key=f"down-{first.uid}").click().run()
                self.assertFalse(app.exception)
                self.assertEqual([item.uid for item in app.session_state["preparation_items"]],
                                 [identities[1], identities[0], identities[2]])
                self.assertEqual(third.moment, "Envoi")
                self.assertEqual(third.verses, ["C1", "C2", "C3"])
                self.assertEqual(first.moment, "Chant d’entrée")
                self.assertEqual(first.verses, ["C1"])
                self.assertEqual(app.selectbox(key=f"sheet_moment_{first.uid}").value, first.moment)
                self.assertEqual(app.selectbox(key=f"sheet_moment_{second.uid}").value, second.moment)
                # Les anciens champs positionnels ne pilotent plus les objets.
                app.session_state["sheet_moment_0"] = "Sanctus"
                app.button(key=f"down-{first.uid}").click().run()
                app.button(key=f"up-{first.uid}").click().run()
                app.selectbox(key=f"sheet_moment_{first.uid}").select("Psaume").run()
                app.button(key=f"up-{first.uid}").click().run()
                self.assertEqual(app.session_state["preparation_items"][0].uid, first.uid)
                self.assertEqual(app.session_state["preparation_items"][0].moment, "Psaume")
                self.assertEqual(second.moment, "Offertoire")
                app.button(key=f"remove-{second.uid}").click().run()
                self.assertFalse(app.exception)
                items = app.session_state["preparation_items"]
                self.assertEqual([item.uid for item in items], [first.uid, third.uid])
                for field in ("song_order", "song_moments", "song_verses"):
                    self.assertNotIn(field, app.session_state)
                expected = deepcopy([item.record() for item in items])
                next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
                self.assertFalse(app.exception)
                html = app.session_state["generated_song_sheet"][1].decode()
                order = [item.path for item in items]
                self.assertEqual(moments_from_contents(html, order, catalog), [item.moment for item in items])
                self.assertEqual(verses_from_contents(html, order, catalog), [item.verses for item in items])
                identifier = app.session_state["preparation_identifier"]
                saved = load_preparation(root / ".cantus-drafts", identifier)
                self.assertEqual(json.loads(encode_preparation(saved))["preparation"]["songs"], expected)
                restored = AppTest.from_string(script, default_timeout=20)
                restored.query_params["preparation"] = identifier
                restored.run()
                self.assertFalse(restored.exception)
                self.assertEqual([item.record() for item in restored.session_state["preparation_items"]], expected)
                self.assertTrue(all(item.title == "Chant" for item in restored.session_state["preparation_items"]))


if __name__ == "__main__":
    unittest.main()
