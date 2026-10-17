"""確認用データ（tests/fixtures/preview_data.json）から preview.html を作る。

画面の確認専用。実行すると、プロジェクトのフォルダに preview.html ができる。
使い方:  python tests/make_preview.py
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from build import render_html  # noqa: E402


def make_preview(now=None):
    """確認用データを、いまの時刻からの「◯時間前」に直して、ページの文字列を返す。"""
    now = now or datetime.now(timezone.utc)
    with open(os.path.join(HERE, "fixtures", "preview_data.json"), encoding="utf-8") as f:
        articles = json.load(f)
    for a in articles:
        a["published"] = (now - timedelta(hours=a.pop("hours_ago"))).isoformat()
    with open(os.path.join(ROOT, "data", "services.json"), encoding="utf-8") as f:
        services = json.load(f)
    with open(os.path.join(ROOT, "template.html"), encoding="utf-8") as f:
        template = f.read()
    return render_html(template, articles, services, now)


if __name__ == "__main__":
    with open(os.path.join(ROOT, "preview.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(make_preview())
    print("preview.html を作りました。")
