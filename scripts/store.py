"""集めた記事を data/articles.json に14日分ためておく部品。"""
import json
import os
from datetime import datetime, timedelta, timezone


def _parse(iso):
    dt = datetime.fromisoformat(iso)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load_articles(path):
    """記事の一覧を読む。ファイルがない・空のときは空の一覧。壊れているときは ValueError。"""
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()
        if not text:
            return []
        data = json.loads(text)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"{path} を読めませんでした") from e
    if not isinstance(data, list):
        raise ValueError(f"{path} を読めませんでした")
    return data


def save_articles(path, articles):
    """新しい順に並べて、日本語のまま書き出す。"""
    ordered = sorted(articles, key=lambda a: _parse(a["published"]), reverse=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ordered, f, ensure_ascii=False, indent=2)
        f.write("\n")


def merge_articles(existing, new, now, keep_days=14):
    """既存と新しい記事をURLで1件にまとめ、keep_days日より古いものを除いて新しい順に返す。"""
    merged = {}
    for article in existing:
        merged[article["url"]] = dict(article)
    for article in new:
        article = dict(article)
        old = merged.get(article["url"])
        if old is not None and _parse(old["published"]) < _parse(article["published"]):
            article["published"] = old["published"]
        merged[article["url"]] = article

    limit = now - timedelta(days=keep_days)
    result = []
    for article in merged.values():
        published = _parse(article["published"])
        if published > now:
            article["published"] = now.isoformat()
            published = now
        if published >= limit:
            result.append(article)
    result.sort(key=lambda a: _parse(a["published"]), reverse=True)
    return result
