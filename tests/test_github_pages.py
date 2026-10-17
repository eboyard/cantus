from dataclasses import replace
from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from xml.etree import ElementTree

from streamlit.testing.v1 import AppTest

from scripts.github_pages import prepare_pages_export, save_pages_export


class GitHubPagesTests(unittest.TestCase):
    def prepare(self, document=b"<!doctype html><html>Paroles</html>", parish="Sainte-Thérèse Lyon", day=date(2026, 10, 18)):
        return prepare_pages_export(document, parish, day, "https://eboyard.github.io/cantus/")

    def test_archive_and_url_preserve_parish_date_and_document(self):
        export = self.prepare()
        self.assertEqual(export.url, "https://eboyard.github.io/cantus/sainte-therese-lyon/2026-10-18/")
        with ZipFile(BytesIO(export.archive)) as archive:
            self.assertEqual(set(archive.namelist()), {
                "docs/sainte-therese-lyon/2026-10-18/index.html",
                "docs/sainte-therese-lyon/2026-10-18/qr.svg", "docs/.nojekyll",
            })
            self.assertEqual(archive.read("docs/sainte-therese-lyon/2026-10-18/index.html"), export.document)
            self.assertEqual(archive.read("docs/sainte-therese-lyon/2026-10-18/qr.svg"), export.qr)
        self.assertEqual(ElementTree.fromstring(export.qr).tag, "{http://www.w3.org/2000/svg}svg")

    def test_replacement_is_explicit_and_keeps_other_sheets(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "docs"
            export = self.prepare()
            target = save_pages_export(export, root)
            next_week = save_pages_export(self.prepare(day=date(2026, 10, 25)), root)
            other_parish = save_pages_export(self.prepare(parish="Saint-Pierre"), root)
            with self.assertRaisesRegex(ValueError, "existe déjà"):
                save_pages_export(replace(export, document=b"Nouveau"), root)
            self.assertEqual(target.read_bytes(), export.document)
            save_pages_export(replace(export, document=b"Nouveau"), root, replace=True)
            self.assertEqual(target.read_bytes(), b"Nouveau")
            self.assertEqual(next_week.read_bytes(), export.document)
            self.assertEqual(other_parish.read_bytes(), export.document)
            self.assertTrue((root / ".nojekyll").exists())

    def test_invalid_configuration_and_escaping_output_path_are_rejected(self):
        for url in ("", "http://example.org", "https://site.org/?query=1", "https://site.org/#fragment", "https://user:secret@site.org"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                prepare_pages_export(b"HTML", "Saint-Pierre", date(2026, 10, 18), url)
        with self.assertRaises(ValueError):
            self.prepare(parish="   ")
        with TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                save_pages_export(replace(self.prepare(), path="../../ailleurs"), Path(directory) / "docs")

    def test_streamlit_export_and_local_save(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "chant.md"
            source.write_text("**Gloire à Toi !**", encoding="utf-8")
            with patch("app.ROOT", root), patch("app.song_catalog", return_value={"chant": ("Un chant", source)}):
                app = AppTest.from_string("from app import main\nmain()")
                app.session_state["song_order"] = ["chant"]
                app.run()
                next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
                app.text_input(key="pages_parish").set_value("Saint-Pierre")
                app.date_input[0].set_value(date(2026, 10, 18)).run()
                next(button for button in app.button if button.label == "Préparer pour GitHub Pages").click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.error), 0)
                export = app.session_state["pages_export"][1]
                self.assertIn(b"<strong>Gloire", export.document)
                self.assertIn("18/10/2026", export.document.decode("utf-8"))
                self.assertEqual(len(app.get("image")), 1)
                next(button for button in app.button if button.label == "Enregistrer dans docs/").click().run()
                self.assertEqual(len(app.error), 0)
                self.assertEqual((root / "docs/saint-pierre/2026-10-18/index.html").read_bytes(), export.document)
                app.text_input(key="pages_parish").set_value("Saint-Paul").run()
                self.assertFalse(any(button.label == "Enregistrer dans docs/" for button in app.button))


if __name__ == "__main__":
    unittest.main()
