from datetime import date
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import URLError

from scripts.aelf import load_aelf_masses, parse_aelf_response, preferred_psalm_key, psalm_catalog
from scripts.lyrics_format import formatted_lines
from scripts.markdown_to_pptx import build_song_parts, plain_text
from scripts.psautier import INDEX, _download, format_stanza, format_stanzas
from scripts.sheet_library import aelf_psalms_from_contents
from scripts.song_sheet import create_song_sheet


FIXTURES = Path(__file__).parent / "fixtures"
DAY = date(2026, 11, 15)


def fixture(number):
    return (FIXTURES / f"psautier_{number}.html").read_text(encoding="utf-8")


class PsautierTests(unittest.TestCase):
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
