import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from store import load_articles, merge_articles, save_articles  # noqa: E402

NOW = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)


def art(url, published, **kw):
    base = {
        "title": "t",
        "published": published.isoformat(),
        "site": "s",
        "summary": "",
        "url": url,
        "category": "chat",
        "service": "",
    }
    base.update(kw)
    return base


class MergeTest(unittest.TestCase):
    def test_merge_dedupes_by_url_and_keeps_oldest_published(self):
        old = art("https://e.com/1", NOW - timedelta(days=2), category="chat")
        new = art("https://e.com/1", NOW - timedelta(days=1), category="video", service="Sora")
        result = merge_articles([old], [new], NOW)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["published"], old["published"])
        self.assertEqual(result[0]["category"], "video")
        self.assertEqual(result[0]["service"], "Sora")

    def test_merge_drops_articles_older_than_14_days(self):
        exactly = art("https://e.com/a", NOW - timedelta(days=14))
        too_old = art("https://e.com/b", NOW - timedelta(days=14, seconds=1))
        result = merge_articles([exactly, too_old], [], NOW)
        self.assertEqual([a["url"] for a in result], ["https://e.com/a"])

    def test_merge_clamps_future_published_to_now(self):
        future = art("https://e.com/f", NOW + timedelta(days=3))
        result = merge_articles([], [future], NOW)
        self.assertEqual(result[0]["published"], NOW.isoformat())

    def test_merge_sorted_newest_first(self):
        a = art("https://e.com/a", NOW - timedelta(days=3))
        b = art("https://e.com/b", NOW - timedelta(days=1))
        c = art("https://e.com/c", NOW - timedelta(days=2))
        result = merge_articles([a, b], [c], NOW)
        self.assertEqual([x["url"] for x in result], ["https://e.com/b", "https://e.com/c", "https://e.com/a"])


class LoadSaveTest(unittest.TestCase):
    def test_load_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load_articles(os.path.join(d, "none.json")), [])

    def test_load_broken_json_raises_with_path(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "articles.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write("[{")
            with self.assertRaises(ValueError) as cm:
                load_articles(p)
            self.assertIn(p, str(cm.exception))

    def test_save_then_load_roundtrip_keeps_japanese(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "articles.json")
            data = [art("https://e.com/1", NOW, title="日本語のタイトル")]
            save_articles(p, data)
            with open(p, encoding="utf-8") as f:
                self.assertIn("日本語のタイトル", f.read())
            self.assertEqual(load_articles(p), data)


if __name__ == "__main__":
    unittest.main()
