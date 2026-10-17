import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "scripts"))
import build  # noqa: E402

FIX = os.path.join(HERE, "fixtures")
NOW = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)

SERVICES = [
    {"name": "Sora", "category": "video", "price": "paid", "icon": "🌊", "desc": "動画"},
]
TEMPLATE = "<script>var DATA = /*__DATA__*/null;</script>"


def read(name):
    with open(os.path.join(FIX, name), "rb") as f:
        return f.read()


def fake_fetch(table):
    def fetch(url):
        value = table[url]
        if isinstance(value, Exception):
            raise value
        return value

    return fetch


NON_AI_FEED = (
    "<rss><channel><item><title>新型PCが発売</title><link>https://n.example/1</link>"
    "<pubDate>Sat, 17 Oct 2026 14:00:00 GMT</pubDate><description>PCの話</description>"
    "</item></channel></rss>"
).encode("utf-8")

SOURCES = [
    {"name": "AI専門", "url": "https://a.example/rss", "ai_only": True},
    {"name": "総合", "url": "https://b.example/atom", "ai_only": False},
]


class CollectTest(unittest.TestCase):
    def test_collect_filters_non_ai_from_general_sites_but_keeps_ai_only_site(self):
        table = {
            "https://a.example/rss": NON_AI_FEED,
            "https://b.example/atom": read("atom_sample.xml"),
        }
        articles, failed = build.collect(SOURCES, SERVICES, fake_fetch(table))
        titles = sorted(a["title"] for a in articles)
        self.assertEqual(titles, ["AIエージェントの安全な実行", "新型PCが発売"])
        self.assertEqual(failed, [])
        for a in articles:
            self.assertIsInstance(a["published"], str)
            self.assertEqual(a["category"], "uncategorized")

    def test_collect_one_site_fails_others_continue(self):
        table = {
            "https://a.example/rss": OSError("通信できません"),
            "https://b.example/atom": read("atom_sample.xml"),
        }
        articles, failed = build.collect(SOURCES, SERVICES, fake_fetch(table))
        self.assertEqual(failed, ["AI専門"])
        self.assertEqual(len(articles), 1)

    def test_collect_all_fail_raises(self):
        table = {
            "https://a.example/rss": OSError("x"),
            "https://b.example/atom": b"<broken",
        }
        with self.assertRaises(RuntimeError):
            build.collect(SOURCES, SERVICES, fake_fetch(table))

    def test_collect_assigns_service_and_category(self):
        table = {
            "https://a.example/rss": read("rss_sample.xml"),
            "https://b.example/atom": read("atom_sample.xml"),
        }
        articles, _ = build.collect(SOURCES, SERVICES, fake_fetch(table))
        sora = [a for a in articles if a["title"] == "Soraの新機能"][0]
        self.assertEqual((sora["category"], sora["service"]), ("video", "Sora"))


class RenderTest(unittest.TestCase):
    def article(self, **kw):
        base = {
            "title": "t",
            "published": NOW.isoformat(),
            "site": "s",
            "summary": "",
            "url": "https://e.com/1",
            "category": "video",
            "service": "Sora",
        }
        base.update(kw)
        return base

    def test_render_html_embeds_json_and_escapes_script_end(self):
        html = build.render_html(TEMPLATE, [self.article(title="</script><b>x")], SERVICES, NOW)
        self.assertEqual(html.count("</script>"), 1)  # テンプレート自身の閉じタグだけ
        self.assertNotIn("/*__DATA__*/", html)
        body = html.split("var DATA = ", 1)[1].rsplit(";</script>", 1)[0]
        data = json.loads(body)
        self.assertEqual(data["articles"][0]["title"], "</script><b>x")
        self.assertEqual(data["builtAt"], NOW.isoformat())

    def test_render_html_adds_price_from_service(self):
        html = build.render_html(
            TEMPLATE, [self.article(), self.article(url="https://e.com/2", service="")], SERVICES, NOW
        )
        body = html.split("var DATA = ", 1)[1].rsplit(";</script>", 1)[0]
        prices = [a["price"] for a in json.loads(body)["articles"]]
        self.assertEqual(prices, ["paid", ""])

    def test_render_html_without_placeholder_raises(self):
        with self.assertRaises(ValueError):
            build.render_html("<p>no placeholder</p>", [], SERVICES, NOW)


class PreviewTest(unittest.TestCase):
    def test_render_html_with_preview_data(self):
        sys.path.insert(0, HERE)
        from make_preview import make_preview

        html = make_preview(NOW)
        self.assertNotIn("/*__DATA__*/", html)
        self.assertEqual(html.count("</script>"), 1)  # データ中の </script> が出力に混ざらない


class ConfigTest(unittest.TestCase):
    def test_load_json_config_bad_json_message_mentions_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "services.json")
            with open(p, "w", encoding="utf-8") as f:
                f.write('[{"name": "x",}]')
            with self.assertRaises(ValueError) as cm:
                build.load_json_config(p)
            self.assertIn(p, str(cm.exception))
            self.assertIn("カンマ", str(cm.exception))


class MainTest(unittest.TestCase):
    def make_root(self, d):
        os.makedirs(os.path.join(d, "data"))
        with open(os.path.join(d, "template.html"), "w", encoding="utf-8") as f:
            f.write(TEMPLATE)
        shutil.copy(os.path.join(HERE, "..", "data", "services.json"), os.path.join(d, "data", "services.json"))
        with open(os.path.join(d, "data", "sources.json"), "w", encoding="utf-8") as f:
            json.dump(SOURCES, f, ensure_ascii=False)
        with open(os.path.join(d, "data", "articles.json"), "w", encoding="utf-8") as f:
            f.write("[]")

    def test_main_writes_index_and_articles_json(self):
        table = {
            "https://a.example/rss": read("rss_sample.xml"),
            "https://b.example/atom": read("atom_sample.xml"),
        }
        with tempfile.TemporaryDirectory() as d:
            self.make_root(d)
            code = build.main(d, fake_fetch(table), NOW)
            self.assertEqual(code, 0)
            self.assertTrue(os.path.exists(os.path.join(d, "index.html")))
            with open(os.path.join(d, "data", "articles.json"), encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(len(saved), 3)

    def test_main_returns_1_when_all_feeds_fail(self):
        table = {"https://a.example/rss": OSError("x"), "https://b.example/atom": OSError("y")}
        with tempfile.TemporaryDirectory() as d:
            self.make_root(d)
            self.assertEqual(build.main(d, fake_fetch(table), NOW), 1)
            self.assertFalse(os.path.exists(os.path.join(d, "index.html")))


if __name__ == "__main__":
    unittest.main()
