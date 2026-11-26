from datetime import date
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from lxml import etree
from streamlit.testing.v1 import AppTest

from ui_helpers import export_downloads

from scripts.word_song_sheet import create_word_song_sheet, TEMPLATE, NS, W


def document(data):
    with ZipFile(BytesIO(data)) as package:
        return etree.fromstring(package.read("word/document.xml"))


class WordSongSheetTests(unittest.TestCase):
    def test_psalm_22_stanzas_have_complete_text_across_both_columns(self):
        path = Path(__file__).resolve().parents[1] / "chants/psaume_22_23.md"
        root = document(create_word_song_sheet("Messe", [("Psaume 22 23", path)], moments=["Psaume"]))
        tables = root.xpath("//w:body/w:tbl", namespaces=NS)[-3:]
        cells = [cell for table in tables for cell in table.xpath("./w:tr/w:tc", namespaces=NS)]
        self.assertEqual(len(cells), 6)
        left, right = [" ".join(" ".join(c.xpath(".//w:t/text()", namespaces=NS)) for c in column)
                       for column in (cells[::2], cells[1::2])]
        self.assertIn("Le Seigneur est mon berger", left)
        self.assertIn("Il me mène vers les eaux tranquilles", right)
        self.assertIn("pour la durée de mes jours.", left)

    def test_single_block_columns_preserve_formatting_across_split(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "psaume.md"
            path.write_text("**<u>Début\\nSuite\\nEncore\\nFin</u>**".replace("\\n", "\n"), encoding="utf-8")
            root = document(create_word_song_sheet("Messe", [("Psaume", path)], moments=["Psaume"]))
        cells = root.xpath("//w:body/w:tbl[last()]/w:tr/w:tc", namespaces=NS)
        for cell in cells:
            self.assertTrue(cell.xpath(".//w:r[w:rPr/w:b and w:rPr/w:u]/w:t", namespaces=NS))
        self.assertEqual("".join(cells[1].xpath(".//w:t/text()", namespaces=NS)), "EncoreFin")

    def test_psalm_long_lines_and_odd_stanza_use_two_columns(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "psaume.md"
            stanzas = [f"Strophe {i} " + "une longue ligne de psaume " * 5 for i in range(1, 4)]
            path.write_text("<!-- refrain -->\n**Seigneur, écoute-nous**\n---\n" +
                            "\n---\n".join(stanzas), encoding="utf-8")
            for size in (9, 10, 11, 12):
                with self.subTest(font_size=size):
                    root = document(create_word_song_sheet(
                        "Messe", [("Psaume", path)], moments=["Psaume"], font_size=size))
                    tables = root.xpath("//w:body/w:tbl", namespaces=NS)[1:]
                    self.assertEqual(len(tables), 2)
                    cells = [table.xpath("./w:tr/w:tc", namespaces=NS) for table in tables]
                    for cell, stanza in zip((cells[0][0], cells[0][1], cells[1][0]), stanzas):
                        self.assertIn(stanza.rstrip(), "".join(cell.xpath(".//w:t/text()", namespaces=NS)))
                    self.assertFalse(cells[1][1].xpath(".//w:t/text()", namespaces=NS))
                    self.assertEqual(len(root.xpath('//w:p[w:pPr/w:pStyle/@w:val="CantusRefrain"]', namespaces=NS)), 1)
            other = document(create_word_song_sheet("Messe", [("Chant", path)], moments=["Envoi"]))
            self.assertEqual(len(other.xpath("//w:body/w:tbl", namespaces=NS)), 1)

    def test_template_generation_preserves_selected_lyrics_styles_and_package(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "chant.md"
            path.write_text('<!-- ordre: R C1 R C2 R C3 -->\n<!-- refrain -->\n**Louange**\n---\n'
                            '<!-- couplet: C1 -->\nBerger d’Isra<u>ë</u>l, écoute\n---\n'
                            '<!-- couplet: C2 -->\nOmettre ce couplet\n---\n'
                            '<!-- couplet: C3 -->\nDernier couplet', encoding="utf-8")
            data = create_word_song_sheet('Premier dimanche de l’Avent — Année A', [("Psaume 79", path)],
                                          day=date(2026, 11, 29), place="Église de test", verses=[["C1", "C3"]])
        root = document(data)
        text = " ".join(root.xpath("//w:t/text()", namespaces=NS))
        self.assertIn("Dimanche 29 novembre 2026", text)
        self.assertIn("Église de test", text)
        self.assertIn("Année A", text)
        self.assertNotIn("Omettre", text)
        self.assertNotIn("{{", text)
        self.assertNotIn("14 Novembre", text)
        self.assertNotIn("Habiter le seuil", text)
        self.assertTrue(root.xpath('//w:r[w:rPr/w:u]/w:t[text()="ë"]', namespaces=NS))
        self.assertEqual(text.count("Louange"), 1)
        self.assertIn("Refrain", text)
        self.assertEqual(len(root.xpath("//w:body/w:tbl", namespaces=NS)), 2)
        with ZipFile(TEMPLATE) as template, ZipFile(BytesIO(data)) as generated:
            self.assertIn(b"wordprocessingml.document.main+xml", generated.read("[Content_Types].xml"))
            for name in template.namelist():
                if name not in {"word/document.xml", "word/styles.xml", "docProps/core.xml", "[Content_Types].xml"}:
                    self.assertEqual(template.read(name), generated.read(name), name)

    def test_word_compacts_c1_c2_c1_sequence(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "kyrie.md"
            path.write_text(
                "<!-- ordre: C1 C2 C1 -->\n"
                "<!-- couplet: C1 -->\nSeigneur, je viens pour implorer\n---\n"
                "<!-- couplet: C2 -->\nÔ Christ, je viens pour implorer",
                encoding="utf-8",
            )
            root = document(create_word_song_sheet("Messe", [("Kyrie", path)]))
        text = " ".join(root.xpath("//w:t/text()", namespaces=NS))
        self.assertEqual(text.count("Seigneur, je viens pour implorer"), 1)
        self.assertIn("1-3.", text)
        self.assertIn("2.", text)
        self.assertIn("Ô Christ, je viens pour implorer", text)
        self.assertLess(text.index("1-3."), text.index("Seigneur, je viens pour implorer"))
        self.assertLess(text.index("2."), text.index("Ô Christ, je viens pour implorer"))

    def test_readings_and_illustration_and_long_verses(self):
        from scripts.aelf import parse_aelf_response
        import json
        payload = json.loads((Path(__file__).parent / "fixtures/aelf_2026_11_15.json").read_text(encoding="utf-8"))
        payload['messes'][0]['lectures'].insert(0, {'type': 'lecture_1', 'intro_lue': 'Lecture avant'})
        payload['messes'][0]['lectures'].append({'type': 'lecture_2', 'intro_lue': 'Lecture après'})
        mass, = parse_aelf_response(payload, date(2026, 11, 15))
        with TemporaryDirectory() as folder:
            psalm, agnus, long = [Path(folder) / name for name in ("ps.md", "agnus.md", "long.md")]
            psalm.write_text(mass.markdown, encoding="utf-8")
            agnus.write_text("Agneau de Dieu", encoding="utf-8")
            long.write_text("\n".join(f"Ligne longue {i}" for i in range(160)), encoding="utf-8")
            from scripts.liturgical_texts import reading_catalog, reading_documents
            readings = list(reading_catalog(reading_documents(mass.markdown), Path(folder)).values())
            result = create_word_song_sheet("Messe", [readings[0], ("Psaume", psalm), readings[1], ("Agnus", agnus), ("Long", long)],
                                            moments=["", "Psaume", "", "Agneau de Dieu", "Envoi"], font_size=10)
        root = document(result)
        text = " ".join(root.xpath("//w:t/text()", namespaces=NS))
        self.assertLess(text.index("Lecture avant"), text.index("Heureux"))
        self.assertLess(text.index("Heureux"), text.index("Lecture après"))
        self.assertIn("Ligne longue 159", text)
        self.assertEqual(len(root.xpath("//*[local-name()='blip']")), 2)
        self.assertFalse(root.xpath('//w:p[w:r/w:t="Ligne longue 0"]/w:pPr/w:keepLines', namespaces=NS))

    def test_validation_and_missing_template_slots(self):
        with self.assertRaises(ValueError):
            create_word_song_sheet("Messe", [])
        with TemporaryDirectory() as folder:
            path = Path(folder) / "chant.md"
            path.write_text("Paroles", encoding="utf-8")
            for arguments in ({"font_size": 8}, {"moments": []}, {"moments": ["invalide"]}, {"verses": []}):
                with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                    create_word_song_sheet("Messe", [("Titre", path)], **arguments)
            path.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "aucune parole"):
                create_word_song_sheet("Messe", [("Vide", path)])

    def test_word_download_changes_with_date_and_place_and_remains_independent(self):
        app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20)
        app.session_state["song_order"] = ["chants/kyrie_messe_de_st_augustin.md"]
        app.run()
        next(button for button in app.button if button.label == "Créer la version à imprimer").click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        data = app.session_state["generated_print_sheet"][1]
        self.assertTrue(data.startswith(b"PK"))
        self.assertNotIn("generated_song_sheet", app.session_state)
        self.assertNotIn("generated_presentation", app.session_state)
        self.assertEqual(export_downloads(app)[0].proto.label, "Télécharger la version à imprimer (.docx)")
        app.text_input(key="word_place").set_value("Autre église").run()
        self.assertFalse(export_downloads(app))
        next(button for button in app.button if button.label == "Créer la version à imprimer").click().run()
        self.assertIn("Autre église", " ".join(document(app.session_state["generated_print_sheet"][1]).xpath("//w:t/text()", namespaces=NS)))
        with patch("app.load_aelf_masses", side_effect=ValueError("AELF indisponible")):
            app.date_input(key="celebration_date").set_value(date(2026, 11, 29)).run()
        self.assertFalse(app.exception)
        self.assertFalse(export_downloads(app))


if __name__ == "__main__":
    unittest.main()
