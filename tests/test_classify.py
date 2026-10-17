import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from classify import classify, find_service, is_ai_related  # noqa: E402

SERVICES = [
    {"name": "Claude", "category": "chat", "price": "mid"},
    {"name": "Sora", "category": "video", "price": "paid"},
    {"name": "Midjourney", "category": "image", "price": "paid"},
    {"name": "Canva のAI機能", "aliases": ["Canva"], "category": "image", "price": "mid"},
    {"name": "Kling", "category": "video", "price": "mid"},
]


class IsAiRelatedTest(unittest.TestCase):
    def test_ai_word_alone_is_ai_related(self):
        self.assertTrue(is_ai_related("生成AIの活用が広がる", "", SERVICES))

    def test_ai_inside_other_word_is_not_ai(self):
        self.assertFalse(is_ai_related("SAILで海へ", "MAINの話", SERVICES))

    def test_service_name_is_ai_related(self):
        self.assertTrue(is_ai_related("Soraの新機能", "", SERVICES))

    def test_unrelated_article_is_not_ai_related(self):
        self.assertFalse(is_ai_related("新型ゲーミングPCが発売", "", SERVICES))


class FindServiceTest(unittest.TestCase):
    def test_find_service_prefers_title_over_summary(self):
        s = find_service("Claudeの話", "Soraも登場", SERVICES)
        self.assertEqual(s["name"], "Claude")

    def test_find_service_earliest_in_title(self):
        s = find_service("SoraとClaudeを比べる", "", SERVICES)
        self.assertEqual(s["name"], "Sora")

    def test_find_service_case_insensitive_and_alias(self):
        self.assertEqual(find_service("midjourney v8", "", SERVICES)["name"], "Midjourney")
        self.assertEqual(find_service("Canvaで作る", "", SERVICES)["name"], "Canva のAI機能")

    def test_find_service_word_boundary(self):
        self.assertIsNone(find_service("Klingonの話", "", SERVICES))

    def test_find_service_uses_summary_when_title_has_none(self):
        s = find_service("新機能の紹介", "Soraが使えます", SERVICES)
        self.assertEqual(s["name"], "Sora")


class ClassifyTest(unittest.TestCase):
    def test_classify_by_service(self):
        self.assertEqual(classify("Soraが進化", "", SERVICES), ("video", "Sora"))

    def test_classify_by_category_word(self):
        self.assertEqual(classify("画像生成が進化", "", SERVICES), ("image", ""))

    def test_classify_uncategorized(self):
        self.assertEqual(classify("AIの利用実態調査", "", SERVICES), ("uncategorized", ""))


if __name__ == "__main__":
    unittest.main()
