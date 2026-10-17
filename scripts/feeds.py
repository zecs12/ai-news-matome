"""RSS 2.0 / Atom を読んで、記事の下書き（dict）に変換する部品。"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    """HTMLからタグを取り除き、文字だけを集める。script/style の中身は捨てる。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def clean_summary(raw, limit=100):
    """HTMLタグと特殊文字を処理し、空白を整えて、limit文字を超えたら「…」を付けて切る。

    limit が None のときは切らない。
    """
    parser = _TextExtractor()
    parser.feed(raw or "")
    parser.close()
    text = " ".join("".join(parser.parts).split())
    text = re.sub(r"\s*続きを読む(\.\.\.|…)?$", "", text)  # GIGAZINE などの定型句
    if limit is not None and len(text) > limit:
        text = text[:limit] + "…"
    return text


def _local(tag):
    """'{namespace}name' から name だけを取り出す。"""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def _child_text(node, *names):
    for child in node:
        if _local(child.tag) in names and child.text and child.text.strip():
            return child.text.strip()
    return ""


def _parse_date(text):
    if not text:
        return None
    try:
        dt = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        dt = None
    if dt is None:
        try:
            dt = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _entry_url(node):
    for child in node:
        if _local(child.tag) != "link":
            continue
        href = child.get("href")
        if href:  # Atom
            if child.get("rel", "alternate") == "alternate":
                return href.strip()
        elif child.text and child.text.strip():  # RSS
            return child.text.strip()
    return ""


def parse_feed(xml_bytes, site):
    """RSS 2.0 か Atom のXMLを読み、記事のリストを返す。

    公開日が読めない記事、URLが http/https でない記事は含めない。
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ValueError("RSSを読めませんでした") from e

    articles = []
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        url = _entry_url(node)
        if not re.match(r"https?://", url):
            continue
        published = _parse_date(
            _child_text(node, "pubDate", "date", "published", "updated")
        )
        if published is None:
            continue
        articles.append(
            {
                "title": clean_summary(_child_text(node, "title"), limit=None),
                "published": published,
                "summary": clean_summary(_child_text(node, "description", "summary")),
                "url": url,
                "site": site,
            }
        )
    return articles
