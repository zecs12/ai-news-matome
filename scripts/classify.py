"""記事がAI関連か、どのサービス・分野の話かを判定する部品。"""
import re

# AIを示す言葉。英字だけの言葉は、前後が英数字のときは当たりにしない（SAIL や MAIN を除く）。
AI_WORDS = ("AI", "人工知能", "生成AI", "機械学習", "大規模言語モデル", "LLM", "ChatGPT", "エージェント")

# 分野を示す言葉。image → video → chat の順に調べる。
CATEGORY_WORDS = {
    "image": ("画像生成", "イラスト生成", "画像AI", "AI画像"),
    "video": ("動画生成", "ビデオ生成", "動画AI", "AI動画"),
    "chat": ("チャットAI", "コード生成", "AIチャット", "コーディングAI", "AIコーディング"),
}


def _find(text, word, ignore_case):
    """text の中で word が最初に出る位置を返す。なければ -1。"""
    if word.isascii():
        flags = re.IGNORECASE if ignore_case else 0
        m = re.search(
            r"(?<![A-Za-z0-9])" + re.escape(word) + r"(?![A-Za-z0-9])", text, flags
        )
        return m.start() if m else -1
    if ignore_case:
        return text.lower().find(word.lower())
    return text.find(word)


def _names(service):
    return [service["name"]] + list(service.get("aliases", []))


def _service_pos(text, service):
    positions = [p for p in (_find(text, n, True) for n in _names(service)) if p >= 0]
    return min(positions) if positions else -1


def find_service(title, summary, services):
    """タイトルを先に、次に説明文を調べ、最初に出てくるサービスを返す。なければ None。"""
    for text in (title, summary):
        best, best_pos = None, -1
        for service in services:
            pos = _service_pos(text, service)
            if pos >= 0 and (best is None or pos < best_pos):
                best, best_pos = service, pos
        if best is not None:
            return best
    return None


def is_ai_related(title, summary, services):
    """AIを示す言葉か、サービス名が入っていれば True。"""
    text = title + "\n" + summary
    if any(_find(text, w, False) >= 0 for w in AI_WORDS):
        return True
    return find_service(title, summary, services) is not None


def classify(title, summary, services):
    """(分野, サービス名) を返す。判別できなければ ("uncategorized", "")。"""
    service = find_service(title, summary, services)
    if service is not None:
        return service["category"], service["name"]
    text = title + "\n" + summary
    for category in ("image", "video", "chat"):
        if any(_find(text, w, False) >= 0 for w in CATEGORY_WORDS[category]):
            return category, ""
    return "uncategorized", ""
