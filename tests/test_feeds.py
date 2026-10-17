import os
import sys
import unittest
from datetime import timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from feeds import clean_summary, parse_feed  # noqa: E402

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def read(name):
    with open(os.path.join(FIX, name), "rb") as f:
        return f.read()


class CleanSummaryTest(unittest.TestCase):
    def test_clean_summary_strips_tags_and_entities(self):
        self.assertEqual(clean_summary('<p><img src="a.png">A &amp; B</p>'), "A & B")

    def test_clean_summary_truncates_to_100_with_ellipsis(self):
        result = clean_summary("あ" * 150)
        self.assertEqual(len(result), 101)
        self.assertTrue(result.endswith("…"))

    def test_clean_summary_exact_100_not_truncated(self):
        self.assertEqual(clean_summary("あ" * 100), "あ" * 100)

    def test_clean_summary_removes_trailing_read_more(self):
        self.assertEqual(clean_summary("報告しています。続きを読む..."), "報告しています。")
        self.assertEqual(clean_summary("報告しています。 続きを読む…"), "報告しています。")

    def test_clean_summary_empty_when_only_html(self):
        self.assertEqual(clean_summary('<img src="a.png">'), "")


class ParseFeedTest(unittest.TestCase):
    def test_parse_rss_three_items_one_dropped(self):
        items = parse_feed(read("rss_sample.xml"), "テストサイト")
        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["published"].hour, 8)  # +0900 の17:00 は UTC の08:00
        self.assertEqual(first["published"].tzinfo, timezone.utc)
        self.assertEqual(first["site"], "テストサイト")
        self.assertEqual(first["summary"], "A & B の話")

    def test_parse_atom(self):
        items = parse_feed(read("atom_sample.xml"), "Atom")
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["published"].tzinfo, timezone.utc)
        self.assertTrue(items[0]["url"].startswith("http"))

    def test_parse_rejects_non_http_url(self):
        xml = (
            "<rss><channel><item><title>x</title>"
            "<link>javascript:alert(1)</link>"
            "<pubDate>Sat, 17 Oct 2026 14:00:00 GMT</pubDate>"
            "</item></channel></rss>"
        ).encode("utf-8")
        self.assertEqual(parse_feed(xml, "x"), [])

    def test_parse_broken_xml_raises(self):
        with self.assertRaises(ValueError):
            parse_feed(b"<rss><item>", "x")


if __name__ == "__main__":
    unittest.main()
