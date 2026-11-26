from dataclasses import replace
from datetime import date, timedelta
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import URLError

from streamlit.testing.v1 import AppTest

from scripts.aelf import load_aelf_masses, parse_aelf_response, preferred_psalm_key, psalm_catalog
from scripts.lyrics_format import formatted_lines
from scripts.markdown_to_pptx import build_song_parts, plain_text, read_title
from scripts.psautier import INDEX, _download, format_stanza, format_stanzas, import_psalm, parse_index, parse_psalm
from scripts.sheet_library import aelf_psalms_from_contents, songs_from_contents
from scripts.song_sheet import create_song_sheet


FIXTURES = Path(__file__).parent / "fixtures"
DAY = date(2026, 11, 15)


def fixture(number):
    return (FIXTURES / f"psautier_{number}.html").read_text(encoding="utf-8")


class PsautierTests(unittest.TestCase):
    def test_ui_date_and_mass_preselect_psautier_and_preserve_manual_choice(self):
        payload = json.loads((FIXTURES / "aelf_2026_11_15.json").read_text(encoding="utf-8"))
        mass, = parse_aelf_response(payload, DAY)
        payload["messes"].append(json.loads(json.dumps(payload["messes"][0])))
        for reading in payload["messes"][1]["lectures"]:
            if reading.get("type") == "psaume":
                reading["ref"] = "Ps 79 (80), 2ac.3bc"
        variants = parse_aelf_response(payload, DAY)
        root = Path(__file__).resolve().parents[1]
        catalog = {"entry": ("Entrée", root / "chants/habiter_le_seuil_de_ta_maison_seigneur.md")}
        with TemporaryDirectory() as directory, patch("app.ROOT", Path(directory)), \
                patch("app.song_catalog", side_effect=lambda: dict(catalog)), \
                patch("app.load_aelf_masses", return_value=variants) as fetch, \
                patch("app.import_psalm") as download:
            app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20)
            app.session_state["celebration_date"] = DAY - timedelta(days=1)
            app.run()
            self.assertIsNone(app.selectbox(key="psautier_choice").value)
            fetch.assert_not_called()
            app.date_input(key="celebration_date").set_value(DAY).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.selectbox(key="psautier_choice").value, "127")
            app.selectbox(key="psautier_choice").select("at40").run()
            app.run()
            self.assertEqual(app.selectbox(key="psautier_choice").value, "at40")
            app.selectbox(key="aelf_mass_choice").select(variants[1].key).run()
            self.assertEqual(app.selectbox(key="psautier_choice").value, "79")
            fetch.side_effect = ValueError("AELF indisponible")
            app.date_input(key="celebration_date").set_value(DAY + timedelta(days=1)).run()
            self.assertEqual(app.selectbox(key="psautier_choice").value, "79")
            fetch.side_effect = None
            fetch.return_value = [replace(mass, reference="Is 12, 2-6")]
            app.date_input(key="celebration_date").set_value(DAY).run()
            self.assertFalse(app.exception)
            self.assertIsNone(app.selectbox(key="psautier_choice").value)
            self.assertTrue(app.button(key="add_psautier").disabled)
            self.assertEqual(app.session_state["song_order"], [])
            download.assert_not_called()

    def test_index_includes_split_psalms_and_canticles_and_rejects_external_pages(self):
        document = ('<select id="navigationHaut"><option value="ignored"></select>'
                    '<select id="navigationBas">'
                    '<option value="Psaume_151_s_Psaume_autographe.html">psaume 151 s</option>'
                    '<option value="Cantique_AT9b_Les_justes.html">cantique AT 9b</option>'
                    '<option value="Cantique_NT0_Les_Beatitudes.html">cantique NT 0</option></select>')
        self.assertEqual(list(parse_index(document)), ["151_s", "at9b", "nt0"])
        for invalid in (document.replace("Psaume_151_s_", "https://example.org/Psaume_151_s_"),
                        document.replace("Psaume_151_s_", "../Psaume_151_s_"), "<select></select>"):
            with self.assertRaises(ValueError):
                parse_index(invalid)

    def test_complete_import_preserves_stanzas_styles_and_source_without_commentary(self):
        document = ('<h1>Cantique</h1><h2>Un titre</h2><table>'
                    '<tr><td></td><td>1</td><td><b>Mon <u>Dieu</u></b> ! *</td></tr>'
                    '<tr><td></td><td></td><td>Une autre ligne.</td></tr>'
                    '<tr><td></td><td></td><td>&nbsp;</td></tr>'
                    '<tr><td></td><td>2</td><td>Écoute <u>encore</u>.</td></tr></table>'
                    '<h2>Doxologie</h2><table><tr><td></td><td></td><td>À exclure.</td></tr></table>'
                    '<div class="copyright">Copyright exemple.<br>Tous droits réservés.</div>')
        markdown = parse_psalm(document, "at40")
        parts = build_song_parts(markdown)
        self.assertEqual(len(parts), 2)
        fragments = [fragment for line in formatted_lines(parts[0].text) for fragment in line]
        self.assertTrue(any(fragment.text == "Dieu" and fragment.bold and fragment.underline
                            for fragment in fragments))
        self.assertEqual(plain_text(parts[0].text), "Mon Dieu ! *\nUne autre ligne.")
        self.assertIn("Écoute <u>encore</u>.", parts[1].text)
        self.assertIn("<!-- titre: Cantique AT 40 — Un titre -->", markdown)
        self.assertIn("<!-- type: Psaume -->", markdown)
        self.assertIn(INDEX["at40"], markdown)
        self.assertIn("Copyright exemple.", markdown)
        self.assertNotIn("À exclure", markdown)
        for invalid in ("", "<h1>Titre</h1><h2>Texte</h2><table></table>"):
            with self.assertRaises(ValueError):
                parse_psalm(invalid, "at40")

    def test_import_persists_and_reuses_local_edits_without_overwriting_other_psalms(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            existing = root / "psaume_128.md"
            existing.write_text("Version de l’équipe", encoding="utf-8")
            with patch("scripts.psautier._download", return_value=fixture(127)) as download:
                path = import_psalm("127", root)
                self.assertEqual(path.name, "psaume_127.md")
                path.write_text(path.read_text(encoding="utf-8") + "\nAjout manuel.\n", encoding="utf-8")
                self.assertEqual(import_psalm("127", root), path)
                download.assert_called_once_with(INDEX["127"])
            self.assertIn("Ajout manuel.", path.read_text(encoding="utf-8"))
            self.assertEqual(existing.read_text(encoding="utf-8"), "Version de l’équipe")
            with patch("scripts.psautier._download", side_effect=URLError("offline")):
                with self.assertRaises(URLError):
                    import_psalm("at40", root)
            self.assertFalse((root / "psaume_at40.md").exists())
            with self.assertRaises(ValueError):
                import_psalm("../outside", root)

    def test_import_uses_psaume_filename_and_reuses_legacy_psautier_file(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("scripts.psautier._download", return_value=fixture(127)) as download:
                path = import_psalm("127", root)
                self.assertEqual(path.name, "psaume_127.md")
                legacy = root / "psautier_127.md"
                legacy.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
                self.assertEqual(import_psalm("127", root), path)
                path.unlink()
                self.assertEqual(import_psalm("127", root), legacy)
                download.assert_called_once_with(INDEX["127"])

    def test_ui_adds_multiple_psalms_and_canticles_without_replacing_and_exports_them(self):
        canticle = ('<h1>Cantique</h1><h2>Un cantique</h2><table>'
                    '<tr><td></td><td>1</td><td>À toi, <u>louange</u>.</td></tr></table>')
        with TemporaryDirectory() as directory:
            root = Path(directory)
            songs = root / "chants"
            songs.mkdir()
            existing = songs / "psaume_62.md"
            existing.write_text("<!-- titre: Psaume 62 -->\nParoles existantes.", encoding="utf-8")
            with patch("app.ROOT", root), patch("app.SONGS_DIR", songs), \
                    patch("scripts.psautier._download", side_effect=[fixture(127), canticle]) as download:
                app = AppTest.from_string("from app import show_preparation\nshow_preparation()", default_timeout=20)
                app.session_state["song_order"] = ["chants/psaume_62.md"]
                app.run()
                for key in ("127", "at40", "127"):
                    app.selectbox(key="psautier_choice").select(key).run()
                    app.button(key="add_psautier").click().run()
                    self.assertFalse(app.exception)
                expected = ["chants/psaume_62.md", "chants/psaume_127.md",
                            "chants/psaume_at40.md", "chants/psaume_127.md"]
                self.assertEqual(app.session_state["song_order"], expected)
                self.assertEqual(app.session_state["song_moments"], ["Psaume"] * 4)
                self.assertEqual(download.call_count, 2)
                next(button for button in app.button if button.label == "Créer la feuille de chants").click().run()
                document = app.session_state["generated_song_sheet"][1].decode()
                self.assertIn("<u>louange</u>", document)
                catalog = {key: (read_title(root / key), root / key) for key in expected}
                self.assertEqual(songs_from_contents(document, catalog), expected)
                before = list(app.session_state["song_order"])
                download.side_effect = URLError("offline")
                app.selectbox(key="psautier_choice").select("nt0").run()
                app.button(key="add_psautier").click().run()
                self.assertEqual(app.session_state["song_order"], before)
                self.assertTrue(any("Impossible d’ajouter" in error.value for error in app.error))

    def test_november_29_unprefixed_reference_and_omitted_half_verses(self):
        payload = json.loads((FIXTURES / "aelf_2026_11_29.json").read_text(encoding="utf-8"))
        original, = parse_aelf_response(payload, date(2026, 11, 29))
        with patch("scripts.psautier._download", return_value=fixture(79)) as download, \
                patch("scripts.aelf.urlopen", return_value=BytesIO(json.dumps(payload).encode())):
            enriched, = load_aelf_masses(date(2026, 11, 29))
        download.assert_called_once_with(INDEX["79"])
        self.assertTrue(enriched.psalm_title.startswith("Psaume 79 (80) —"))
        before, after = build_song_parts(original.markdown), build_song_parts(enriched.markdown)
        self.assertEqual(before[0], after[0])
        self.assertEqual(len(before), len(after))
        couplets = [p for p in after if p.kind == "couplet"]
        self.assertTrue(all(part.text.count("<u>") == 4 for part in couplets))
        self.assertIn("Isra<u>ë</u>l", couplets[0].text)
        self.assertIn("au-dess<u>u</u>s des Kéroubim !", couplets[0].text)
        self.assertNotIn("Joseph", enriched.markdown)
        self.assertNotIn("Éphraïm", enriched.markdown)
        for a, b in zip(before, after):
            self.assertEqual(" ".join(plain_text(a.text).split()), " ".join(plain_text(b.text).split()))
        with TemporaryDirectory() as directory:
            catalog = psalm_catalog({enriched.key: enriched.markdown}, Path(directory))
            html = create_song_sheet(enriched.title, [catalog[enriched.key]]).decode()
            self.assertIn("Isra<u>ë</u>l", html)
            self.assertEqual(aelf_psalms_from_contents(html), {enriched.key: enriched.markdown})

    def test_reference_formats_and_partial_stanza_keep_unmatched_lines(self):
        from scripts.psautier import PSALM_REFERENCE
        for value in ("79 (80), 2ac.3bc", "Ps 79 (80), 2ac.3bc", "Psaume 79, 2", "Ps. 79, 2"):
            self.assertEqual(PSALM_REFERENCE.match(value)[1], "79")
        for value in ("1 S 2, 1", "Is 12, 1", "1 Ch 29, 10"):
            self.assertIsNone(PSALM_REFERENCE.match(value))
        text = "Berger d’Israël, écoute,\nUne ligne différente.\net viens nous sauver."
        result = format_stanza(text, fixture(79))
        self.assertEqual(plain_text(result), text)
        self.assertIn("Isra<u>ë</u>l", result)
        self.assertIn("Une ligne différente.", result)
        self.assertIn("vi<u>e</u>ns", result)

    def test_daily_import_preserves_words_refrain_order_and_team_priority(self):
        payload = json.loads((FIXTURES / "aelf_2026_11_15.json").read_text(encoding="utf-8"))
        original, = parse_aelf_response(payload, DAY)
        with patch("scripts.psautier._download", return_value=fixture(127)), \
                patch("scripts.aelf.urlopen", return_value=BytesIO(json.dumps(payload).encode())):
            enriched, = load_aelf_masses(DAY)
        before, after = build_song_parts(original.markdown), build_song_parts(enriched.markdown)
        self.assertEqual([(p.kind, p.identifier) for p in before], [(p.kind, p.identifier) for p in after])
        self.assertEqual(before[0], after[0])
        for a, b in zip(before, after):
            self.assertEqual(" ".join(plain_text(a.text).split()), " ".join(plain_text(b.text).split()))
        self.assertIn("cr<u>a</u>int", enriched.markdown)
        self.assertIn("Jérusalem\ntous les jo<u>u</u>rs", enriched.markdown)
        self.assertNotIn("Paix sur Israël", enriched.markdown)
        self.assertIn("Mise en forme : https://psautier.org/", enriched.markdown)
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(preferred_psalm_key(enriched, {"chants/psaume_127.md":
                         ("Psaume 127", root / "chants/psaume_127.md")}), "chants/psaume_127.md")
        with TemporaryDirectory() as directory:
            catalog = psalm_catalog({enriched.key: enriched.markdown}, Path(directory))
            html = create_song_sheet(enriched.title, [catalog[enriched.key]]).decode()
            self.assertIn("cr<u>a</u>int", html)
            self.assertEqual(aelf_psalms_from_contents(html), {enriched.key: enriched.markdown})

    def test_117_index_excerpt_preserves_aelf_punctuation_and_no_extra_verses(self):
        text = "La pierre qu’ont rejetée les bâtisseurs\nest devenue la pierre d’angle :\nc’est là l’œuvre du Seigneur,\nla merveille devant nos yeux."
        result = format_stanza(text, fixture(117))
        self.assertEqual(plain_text(result), text)
        self.assertIn("rejet<u>é</u>e", result)
        self.assertIn("œ<u>u</u>vre", result)
        self.assertNotIn("Doxologie", result)
        self.assertEqual(INDEX["117"], "Psaume_117_Le_jour_que_le_Seigneur_a_fait.html")
        self.assertEqual(INDEX["127"], "Psaume_127_Tu_verras_les_fils_de_tes_fils.html")

    def test_unknown_changed_and_ambiguous_passages_are_unchanged(self):
        for text in ("Un texte différent.", "Éternel est son amour !"):
            self.assertEqual(format_stanza(text, fixture(117)), text)
        for reference in ("Is 12, 1-6", "Ps 999, 1", "Ps 151, 1"):
            with patch("scripts.psautier._download") as download:
                self.assertEqual(format_stanzas(reference, ["texte"]), (["texte"], None))
                download.assert_not_called()

    def test_split_psalms_and_unavailable_site(self):
        document = "<h1>Psaume</h1><table><tr><td></td><td>1</td><td>Te<u>x</u>te.</td></tr></table>"
        with patch("scripts.psautier._download", side_effect=["", document]) as download:
            formatted, source = format_stanzas("Ps 18 (19), 1", ["Texte."])
            self.assertEqual(formatted, ["Te<u>x</u>te."])
            self.assertIn(INDEX["18b"], source)
            self.assertEqual(download.call_count, 2)
        for error in (URLError("offline"), TimeoutError(), UnicodeError()):
            with patch("scripts.psautier._download", side_effect=error):
                self.assertEqual(format_stanzas("Ps 127, 1", ["Texte."]), (["Texte."], None))

    def test_only_text_table_and_supported_styles_are_transferred(self):
        document = '<table><tr><td>Navigation</td></tr></table><h1>Psaume</h1><table><tr><td>1</td><td>2</td><td><b>Mon <u>Dieu</u></b><script>intrusion</script></td></tr><tr><td></td><td></td><td>écoute !</td></tr></table><table><tr><td></td><td></td><td>Oraison</td></tr></table>'
        result = format_stanza("Mon Dieu écoute !", document)
        self.assertEqual(plain_text(result), "Mon Dieu\nécoute !")
        fragments = [fragment for line in formatted_lines(result) for fragment in line]
        self.assertTrue(any(fragment.bold and fragment.underline and "Dieu" in fragment.text for fragment in fragments))
        self.assertNotIn("intrusion", result)

    def test_cache_success_retry_failure_and_download_size_limit(self):
        _download.cache_clear()
        self.addCleanup(_download.cache_clear)
        with patch("scripts.psautier.urlopen", side_effect=[URLError("offline"), BytesIO(b"<h1>ok</h1>")]) as get:
            with self.assertRaises(URLError):
                _download(INDEX["127"])
            self.assertEqual(_download(INDEX["127"]), "<h1>ok</h1>")
            _download(INDEX["127"])
            self.assertEqual(get.call_count, 2)
        with patch("scripts.psautier.urlopen", return_value=BytesIO(b"x" * 1_000_001)):
            with self.assertRaises(ValueError):
                _download(INDEX["117"])


if __name__ == "__main__":
    unittest.main()
