"""4つのニュースサイトのRSSを読み、AI記事を選んで、完成ページ index.html を作る。

使い方:  python scripts/build.py
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classify import classify, is_ai_related  # noqa: E402
from feeds import parse_feed  # noqa: E402
from store import load_articles, merge_articles, save_articles  # noqa: E402

USER_AGENT = "AI-News-Matome/1.0"
PLACEHOLDER = "/*__DATA__*/null"


def load_json_config(path):
    """services.json / sources.json のような設定ファイルを読む。"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("not a list")
        return data
    except (OSError, ValueError) as e:
        raise ValueError(
            f"{path} を読めませんでした。カンマ（,）や引用符（\"）の書き間違いがないか確認してください。"
        ) from e


def fetch_url(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def collect(sources, services, fetch=fetch_url):
    """各サイトのRSSから記事を集める。(記事のリスト, 読めなかったサイト名のリスト) を返す。"""
    articles, failed = [], []
    for source in sources:
        try:
            items = parse_feed(fetch(source["url"]), source["name"])
        except Exception:  # 1サイトの失敗で全体を止めない
            failed.append(source["name"])
            continue
        for item in items:
            if not source.get("ai_only") and not is_ai_related(
                item["title"], item["summary"], services
            ):
                continue
            category, service = classify(item["title"], item["summary"], services)
            articles.append(
                {
                    "title": item["title"],
                    "published": item["published"].isoformat(),
                    "site": item["site"],
                    "summary": item["summary"],
                    "url": item["url"],
                    "category": category,
                    "service": service,
                }
            )
    if len(failed) == len(sources):
        raise RuntimeError("すべてのサイトのRSSを読めませんでした")
    return articles, failed


def render_html(template, articles, services, built_at):
    """ひな形の目印を、記事などのデータ（JSON）に置き換えて、完成ページの文字列を返す。"""
    if PLACEHOLDER not in template:
        raise ValueError("template.html にデータを入れる目印がありません")
    prices = {s["name"]: s["price"] for s in services}
    items = []
    for article in articles:
        item = dict(article)
        item["price"] = prices.get(article.get("service", ""), "")
        items.append(item)
    payload = json.dumps(
        {"articles": items, "services": services, "builtAt": built_at.isoformat()},
        ensure_ascii=False,
    )
    payload = payload.replace("<", "\\u003c")  # </script> などで画面が壊れないように
    return template.replace(PLACEHOLDER, payload)


def main(root=".", fetch=fetch_url, now=None):
    now = now or datetime.now(timezone.utc)
    data_dir = os.path.join(root, "data")
    try:
        services = load_json_config(os.path.join(data_dir, "services.json"))
        sources = load_json_config(os.path.join(data_dir, "sources.json"))
        existing = load_articles(os.path.join(data_dir, "articles.json"))
        with open(os.path.join(root, "template.html"), encoding="utf-8") as f:
            template = f.read()
        new, failed = collect(sources, services, fetch)
        articles = merge_articles(existing, new, now)
        html = render_html(template, articles, services, now)
    except (ValueError, RuntimeError, OSError) as e:
        print(f"エラー: {e}")
        return 1

    save_articles(os.path.join(data_dir, "articles.json"), articles)
    with open(os.path.join(root, "index.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    if failed:
        print("読めなかったサイト: " + "、".join(failed))
    print(f"記事 {len(articles)} 件で index.html を作りました。")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    here = os.path.dirname(os.path.abspath(__file__))
    raise SystemExit(main(os.path.dirname(here)))
