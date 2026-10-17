# AIニュースまとめ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 4つの日本語ニュースサイトのRSSから毎日AI記事を集め、サンプルと同じ見た目の静的ページ `index.html` を自動生成して GitHub Pages で公開する。

**Architecture:** Python標準機能だけの小さなビルドプログラムが、RSS取得 → AI判定・分類 → 14日分の保管（`data/articles.json`）→ `template.html` に記事を埋め込んで `index.html` 出力、を行う。ページの動き（タブ・絞り込み・NEW・保存・バックアップ）はテンプレート内のJavaScriptが担当する。GitHub Actions が毎朝6時（JST）にビルドして Pages へ公開する。

**Tech Stack:** Python 3.10以上（標準ライブラリのみ。`unittest`）、素のHTML/CSS/JavaScript、GitHub Actions、GitHub Pages。

**Spec:** `docs/superpowers/specs/2026-10-17-ai-news-matome-design.md`

## Global Constraints

- お金がかかるもの・外部の有料サービスは使わない。Pythonは標準ライブラリのみ（`pip install` を要する部品を入れない）。
- 記事ごとに保存・表示してよいのは、タイトル / 公開日 / サイト名 / 冒頭の説明（100文字以内、切ったときは末尾に「…」）/ 元記事URL（＋分野・サービス名・料金の色）だけ。本文・画像は保存しない。
- 元記事への「元記事を開く（サイト名）」リンクは全記事に付ける。新しいタブで開く（`target="_blank" rel="noopener noreferrer"`）。リンクは `http://` か `https://` のURLだけ許す。
- 分野は `chat` / `image` / `video` / `uncategorized` の4つ。タブ名は「チャット・コード」「画像づくり」「動画づくり」「未分類」（絵文字 💬 🎨 🎬 📂）。
- 料金の色は `free` / `mid` / `paid`、当てはまらなければ色なし（灰色）。
- 公開から14日たった記事は `articles.json` からもページからも消す。1分野（未分類含む）あたり最大8件、新しい順。「NEW」は公開から24時間以内（ページを開いた時刻で判定）。
- 保存した記事は14日・8件の対象外。保存先はブラウザの localStorage のみ。保存した記事が1件以上あり、最後のバックアップから7日以上（または未バックアップ）なら「バックアップを取りましょう」を表示。
- サンプル（`ai-matome-sample.html`）の色・フォント・カード・料金ボタン・用語の説明・暗い画面の切り替えを維持。「これは試作です」の注意書きと「※試作のため…」の注記は載せない。
- RSS取得は1日1回。User-Agent は `AI-News-Matome/1.0`。
- 作業フォルダ `C:\Users\zecs1\Documents\AIニュースまとめ` は現在 git リポジトリではない。**Task 8 まで git commit は行わない**（Task 8 で `git init`）。既存ファイル（`ai-matome-sample.html` など）は削除・変更しない。
- 利用者向けの文言（画面・エラー・README）はすべてやさしい日本語。

## Review Focus

- 説明文が空、またはHTMLタグ・画像だけの記事 → 説明は空文字にして記事自体は載せる（落とさない）。
- タイトルや説明に `<script>` や `&amp;` のような文字がある → 画面を壊さず、文字として表示される。
- `javascript:` で始まるURLの記事、またはバックアップファイル内のそのようなURL → 取り込まず、リンクにもしない。
- 同じ記事が2サイトのRSSに載る、または毎日同じ記事を取り直す → URLが同じなら1件だけ。
- `data/services.json` や `sources.json` の書き間違い（カンマ忘れなど） → 日本語で「どのファイルが読めないか」を表示して止まる。
- 記事が0件の分野 → 「いまこの分野の記事はありません。」を表示。
- localStorage が使えない（シークレットモード等）／壊れたバックアップファイル → ページは動き続け、「保存できません」「このファイルは読み込めません」を表示。
- 公開日が未来になっている記事 → 現在時刻に切り下げて扱う（「◯時間前」が負にならない）。

---

## ファイル構成

| ファイル | 責任 |
|---|---|
| `scripts/feeds.py` | RSS 2.0 / Atom のXMLを読み、記事の下書き（dict）に変換。説明文の掃除と100文字切り |
| `scripts/classify.py` | AI関連判定・サービス名判定・分野判定・料金の色 |
| `scripts/store.py` | `articles.json` の読み書き、URLでの重複排除、14日より古い記事の削除 |
| `scripts/build.py` | 設定ファイル読み込み、4サイト取得、全滅時の失敗、`index.html` 生成（`main()`） |
| `template.html` | ページ本体（CSS・JS込み）。`/*__DATA__*/null` の位置に記事等のJSONを埋め込む |
| `data/services.json` / `data/sources.json` | 手で直す設定 |
| `tests/` | `unittest` と、小さなRSS/Atomのサンプル（`tests/fixtures/`） |

仕様書のファイル表は `build.py` 1本としているが、読みやすさのため上の4つのPythonファイルに分ける（動作は同じ）。

---

### Task 1: 準備（Python確認・設定ファイル・テストの土台）

**Files:**
- Create: `data/services.json`, `data/sources.json`, `data/articles.json`（中身は `[]`）, `tests/__init__.py`, `tests/fixtures/rss_sample.xml`, `tests/fixtures/atom_sample.xml`, `scripts/__init__.py`

**Interfaces:**
- Produces: `data/services.json` = 配列。要素 `{"name","aliases"(省略可),"category","price","icon","desc"}`。サンプルの12サービス（ChatGPT, Claude, Gemini, Microsoft Copilot＝chat／Midjourney, Adobe Firefly, Canva のAI機能, Bing Image Creator＝image／Sora, Runway, Kling, Vrew＝video）を、サンプルの `SERVICES` の絵文字・料金・説明そのままで書く。`aliases` は ChatGPT→`["OpenAI"]` を入れない（会社名だけの記事を誤分類しないため）、Canva のAI機能→`["Canva"]`、Microsoft Copilot→`["Copilot"]`、Bing Image Creator→`["Image Creator"]`。
- Produces: `data/sources.json` = 配列。要素 `{"name","url","ai_only"}`。仕様書 §3 の4サイト（ITmedia AI＋のみ `ai_only: true`）。
- Produces: `tests/fixtures/rss_sample.xml`（RSS 2.0、3件: `+0900` の pubDate、`GMT` の pubDate、pubDateなし1件。説明にCDATA＋`<img>`タグ・`&amp;` を含む）、`atom_sample.xml`（Atom、2件、`2026-10-17T15:27:18Z` 形式、`summary` あり）。

- [ ] **Step 1:** PowerShellで `python --version` を実行し、3.10以上であることを確認する。入っていない／古い場合は作業を止め、利用者に Python の入れ方（公式サイトからのダウンロードとインストール手順。「Add python.exe to PATH」にチェック）を1つずつ案内してから再開する。期待: `Python 3.10` 以上の表示。
- [ ] **Step 2:** 上記の各ファイルを作る。`data/services.json` と `data/sources.json` は UTF-8（BOMなし）、インデント2、`ensure_ascii=False` 相当（日本語をそのまま）で書く。
- [ ] **Step 3:** `python -c "import json;[json.load(open(p,encoding='utf-8')) for p in ['data/services.json','data/sources.json','data/articles.json']];print('ok')"` を実行。期待: `ok`。

---

### Task 2: RSS/Atom の読み取りと説明文の掃除（`scripts/feeds.py`）

**Files:**
- Create: `scripts/feeds.py`
- Test: `tests/test_feeds.py`

**Interfaces:**
- Produces:
  - `clean_summary(raw: str, limit: int = 100) -> str` — HTMLタグ除去、HTMLの特殊文字（`&amp;` 等）を元の文字に戻す、空白・改行を1つの半角スペースにまとめて前後を削る。`limit` を超えるなら `limit` 文字で切り、末尾に「…」を付ける（付けた分を含めて `limit+1` 文字になってよい）。
  - `parse_feed(xml_bytes: bytes, site: str) -> list[dict]` — 戻りの各dictは `{"title": str, "published": datetime（UTCのタイムゾーン付き）, "summary": str, "url": str, "site": str}`。RSS 2.0（`item`、`pubDate`/`dc:date`、`description`、`link`）と Atom（`entry`、`published`/`updated`、`summary`、`link[@rel=alternate]` の `href`）の両方に対応。公開日が読めない、またはURLが `http://`/`https://` でない記事は戻りに含めない。`title` は `clean_summary` と同じ掃除（ただし切らない）。XMLが壊れているときは `ValueError("RSSを読めませんでした")` を投げる。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_feeds.py`（`unittest.TestCase`）:
  - `test_clean_summary_strips_tags_and_entities`: `clean_summary('<p><img src="a.png">A &amp; B</p>') == 'A & B'`
  - `test_clean_summary_truncates_to_100_with_ellipsis`: `'あ'*150` → `len(result)==101` かつ末尾が `'…'`
  - `test_clean_summary_exact_100_not_truncated`: `'あ'*100` はそのまま
  - `test_clean_summary_empty_when_only_html`: `'<img src="a.png">'` → `''`
  - `test_parse_rss_three_items_one_dropped`: `rss_sample.xml` → 件数2（pubDateなしは落ちる）、先頭の `published` が UTC に直っている（`+0900` の 17:00 → 08:00 UTC）、`site` が渡した値。
  - `test_parse_atom`: `atom_sample.xml` → 2件、`published.tzinfo` が UTC、`url` が `http`始まり。
  - `test_parse_rejects_non_http_url`: `<link>javascript:alert(1)</link>` の記事は落ちる。
  - `test_parse_broken_xml_raises`: `b'<rss><item>'` → `ValueError`。
- [ ] **Step 2:** `python -m unittest tests.test_feeds -v` を実行。期待: インポートエラーで FAIL。
- [ ] **Step 3:** `scripts/feeds.py` に上記2関数を実装する。XML解析は `xml.etree.ElementTree`、日付は `email.utils.parsedate_to_datetime`（RSS）と `datetime.fromisoformat`（Atom、`Z` は `+00:00` に置換）、タグ除去は `html.parser.HTMLParser` か正規表現、特殊文字は `html.unescape`。
- [ ] **Step 4:** `python -m unittest tests.test_feeds -v` を実行。期待: すべて PASS。

---

### Task 3: AI判定・サービス判定・分野判定（`scripts/classify.py`）

**Files:**
- Create: `scripts/classify.py`
- Test: `tests/test_classify.py`

**Interfaces:**
- Consumes: `data/services.json` の形（Task 1）。
- Produces:
  - 定数 `AI_WORDS: tuple[str, ...]` = `("AI", "人工知能", "生成AI", "機械学習", "大規模言語モデル", "LLM", "ChatGPT", "エージェント")`。英字の「AI」は前後が英数字でないときだけ当たり（`SAIL` や `MAIN` を除く）。
  - 定数 `CATEGORY_WORDS: dict[str, tuple[str, ...]]` = `{"image": ("画像生成", "イラスト生成", "画像AI", "AI画像"), "video": ("動画生成", "ビデオ生成", "動画AI", "AI動画"), "chat": ("チャットAI", "コード生成", "AIチャット", "コーディングAI", "AIコーディング")}`。
  - `is_ai_related(title: str, summary: str, services: list[dict]) -> bool` — `AI_WORDS` のどれか、またはサービス名（`aliases` 含む）がタイトルか説明に入っていれば True。
  - `find_service(title: str, summary: str, services: list[dict]) -> dict | None` — タイトルで先に探し、複数ならタイトル内で最初に出る位置のサービス。タイトルになければ説明文で同様に。英字の名前は大文字小文字を区別せず、前後が英数字（半角）でない場合だけ当たり。日本語の名前は単純な部分一致。`aliases` も同じ扱い。
  - `classify(title: str, summary: str, services: list[dict]) -> tuple[str, str]` — `(分野, サービス名)`。サービスが当たれば `(そのcategory, name)`。なければ `CATEGORY_WORDS` の順（image → video → chat）で最初に当たった分野と空文字。どれもなければ `("uncategorized", "")`。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_classify.py`（テスト内で小さな `services` リストを作る: Claude＝chat・mid、Sora＝video・paid、Midjourney＝image・paid、Canva のAI機能（aliases `["Canva"]`）＝image・mid）:
  - `test_ai_word_alone_is_ai_related`: タイトル「生成AIの活用が広がる」→ True
  - `test_ai_inside_other_word_is_not_ai`: タイトル「SAILで海へ」「MAINの話」説明も無関係 → False
  - `test_service_name_is_ai_related`: タイトルに「Soraの新機能」→ True
  - `test_unrelated_article_is_not_ai_related`: 「新型ゲーミングPCが発売」→ False
  - `test_find_service_prefers_title_over_summary`: タイトルに Claude、説明に Sora → Claude
  - `test_find_service_earliest_in_title`: タイトル「SoraとClaudeを比べる」→ Sora
  - `test_find_service_case_insensitive_and_alias`: 「midjourney v8」→ Midjourney、「Canvaで作る」→ Canva のAI機能
  - `test_find_service_word_boundary`: 名前 `"Kling"` のとき「Klingon」は当たらない（services に Kling を足して確認）
  - `test_classify_by_service`: Sora を含む記事 → `("video", "Sora")`
  - `test_classify_by_category_word`: 「画像生成が進化」→ `("image", "")`
  - `test_classify_uncategorized`: 「AIの利用実態調査」→ `("uncategorized", "")`
- [ ] **Step 2:** `python -m unittest tests.test_classify -v` を実行。期待: インポートエラーで FAIL。
- [ ] **Step 3:** `scripts/classify.py` を実装する。英字の境界判定は `re.search(r'(?<![A-Za-z0-9])' + re.escape(name) + r'(?![A-Za-z0-9])', text, re.IGNORECASE)`、日本語を含む名前（非ASCII文字を含む名前）は `str.find`。位置は両方式で取り出して最小を採用。
- [ ] **Step 4:** `python -m unittest tests.test_classify -v` を実行。期待: すべて PASS。

---

### Task 4: 記事の保管（`scripts/store.py`）

**Files:**
- Create: `scripts/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Produces: 保管する記事は `dict`: `{"title","published"(ISO文字列 "2026-10-17T08:00:00+00:00"),"site","summary","url","category","service"}`。
  - `load_articles(path: str) -> list[dict]` — ファイルがない・中身が空のときは `[]`。JSONが壊れているときは `ValueError("data/articles.json を読めませんでした")`（パスを文言に含める）。
  - `save_articles(path: str, articles: list[dict]) -> None` — 新しい順に並べて UTF-8・インデント2・日本語そのままで書く。
  - `merge_articles(existing: list[dict], new: list[dict], now: datetime, keep_days: int = 14) -> list[dict]` — URLが同じものは1件（`new` 側の分野・サービス・説明で上書きするが、`published` は古い方を保つ）。`published` が `now` の `keep_days` 日より前のものは除く。`published` が `now` より未来のものは `now` に切り下げる。戻りは新しい順。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_store.py`:
  - `test_merge_dedupes_by_url_and_keeps_oldest_published`
  - `test_merge_drops_articles_older_than_14_days`（ちょうど14日前は残し、14日と1秒前は消す）
  - `test_merge_clamps_future_published_to_now`
  - `test_merge_sorted_newest_first`
  - `test_load_missing_file_returns_empty_list`（一時フォルダを使う）
  - `test_load_broken_json_raises_with_path`
  - `test_save_then_load_roundtrip_keeps_japanese`（保存したファイルを読むと日本語がそのまま入っている）
- [ ] **Step 2:** `python -m unittest tests.test_store -v` を実行。期待: FAIL。
- [ ] **Step 3:** `scripts/store.py` を実装する。
- [ ] **Step 4:** `python -m unittest tests.test_store -v` を実行。期待: すべて PASS。

---

### Task 5: ビルド本体（`scripts/build.py`）

**Files:**
- Create: `scripts/build.py`
- Test: `tests/test_build.py`

**Interfaces:**
- Consumes: `feeds.parse_feed`, `classify.is_ai_related` / `classify`, `store.load_articles` / `merge_articles` / `save_articles`。
- Produces:
  - `load_json_config(path: str) -> list[dict]` — 読めない・配列でないときは `ValueError(f"{path} を読めませんでした。カンマ（,）や引用符（\"）の書き間違いがないか確認してください。")`。
  - `fetch_url(url: str) -> bytes` — `urllib.request`、User-Agent `AI-News-Matome/1.0`、タイムアウト30秒。
  - `collect(sources: list[dict], services: list[dict], fetch=fetch_url) -> tuple[list[dict], list[str]]` — 戻りは `(新しい記事のdictのリスト, 失敗したサイト名のリスト)`。各サイトを取得・解析し、`ai_only` が False のサイトの記事は `is_ai_related` が True のものだけ残し、`classify` で分野とサービスを付け、`published` は ISO 文字列にする。1サイトの失敗（例外）は失敗リストに入れて続行。全サイトが失敗なら `RuntimeError("すべてのサイトのRSSを読めませんでした")`。
  - `render_html(template: str, articles: list[dict], services: list[dict], built_at: datetime) -> str` — `template` の `/*__DATA__*/null` を、`{"articles": [...], "services": [...], "builtAt": ISO文字列}` のJSONに置き換える。各 `articles` の要素には、サービスが当たる場合 `price`（`services.json` の値）、当たらなければ `""` を足す。JSON中の `</` は `<\/` に置換する（`</script>` 対策）。置換位置が見つからなければ `ValueError`。
  - `main(root: str = ".", fetch=fetch_url, now: datetime | None = None) -> int` — 設定読み込み → `collect` → `merge_articles` → `save_articles(data/articles.json)` → `index.html` 書き出し。失敗サイトがあれば標準出力に `読めなかったサイト: …` を出す。終了コード 0（成功・一部失敗）、全滅や設定エラーは日本語メッセージを出して 1。
- スクリプトとして実行できる（`if __name__ == "__main__": raise SystemExit(main())`）。`python scripts/build.py` で、`scripts/` からの相対インポート（`from feeds import …`）が動くよう、先頭で `sys.path` に自分のフォルダを足す。

- [ ] **Step 1: 失敗するテストを書く** — `tests/test_build.py`（ネットワークは使わず、`fetch` に `tests/fixtures/` のXMLを返す関数を渡す）:
  - `test_collect_filters_non_ai_from_general_sites_but_keeps_ai_only_site`
  - `test_collect_one_site_fails_others_continue`（失敗リストにサイト名が入る）
  - `test_collect_all_fail_raises`
  - `test_render_html_embeds_json_and_escapes_script_end`（タイトルに `</script>` を含む記事で、出力に生の `</script>` がデータ部分に現れない）
  - `test_render_html_adds_price_from_service`
  - `test_load_json_config_bad_json_message_mentions_file`
  - `test_main_writes_index_and_articles_json`（一時フォルダに `data/`・`template.html` を用意し、`main` が 0 を返し `index.html` ができる）
  - `test_main_returns_1_when_all_feeds_fail`
- [ ] **Step 2:** `python -m unittest tests.test_build -v` を実行。期待: FAIL。
- [ ] **Step 3:** `scripts/build.py` を実装する。
- [ ] **Step 4:** `python -m unittest discover -s tests -v` を実行。期待: Task 2〜5 のテストがすべて PASS。

---

### Task 6: ページのひな形（`template.html`）

**Files:**
- Create: `template.html`（`ai-matome-sample.html` をもとにした新規ファイル。サンプル自体は変更しない）

**Interfaces:**
- Consumes: `build.render_html` が埋め込むデータ。ページ側では `var DATA = /*__DATA__*/null;` と書く（`render_html` が `/*__DATA__*/null` 全体を置換する）。`DATA.articles[i]` は `{title, published, site, summary, url, category, service, price}`、`DATA.services[i]` は `services.json` の要素。
- Produces: `index.html` の見た目と動き（下記）。ブラウザの localStorage のキーは `aimatome.saved.v1`（保存した記事の配列。要素は `{title, published, site, summary, url, category, service, price, savedAt}`）と `aimatome.lastBackup.v1`（最後にバックアップした時刻のISO文字列）。

サンプルから変えること（それ以外は見た目・CSS・用語の説明・暗い画面の切り替えをそのまま使う）:

- [ ] **Step 1: 見た目の土台** — サンプルの `<head>` と CSS をそのままコピーし、`<title>` は「AIニュースまとめ」にする。`.sample-note` の要素と、サンプルのデータ（`SERVICES`/`ARTICLES` のサンプル）を削除。ヘッダーの文は「いま話題のAIを、やさしく・色つきで。」のまま。
- [ ] **Step 2: タブ4つ** — `CATS` に `uncategorized: {title:"未分類", sub:"どの分野か判別できなかったAIの記事です"}` を足し、タブを 💬 / 🎨 / 🎬 / 📂 の4つに（`.tabs` の `grid-template-columns:repeat(4,1fr)`、`.tab` の文字は 12px、`.tab span` は 20px）。「サービスのしょうかい」は `uncategorized` のとき出さない。
- [ ] **Step 3: 記事カード** — `DATA.articles` を分野で絞り、公開日の新しい順に並べて14日以内のものから最大8件。絞り込みボタンは `price` で判定（`price` が空の記事は「ぜんぶ」のときだけ）。カードは サンプルの `.card`（左の色の帯は `data-price`）。メタ行: NEW（公開から24時間以内、ページを開いた時刻で計算。公開日が未来のときは現在時刻に切り下げ）／料金バッジ（`price` がある時だけ）／サービス名（あれば）／サイト名／「◯時間前」「◯日前」。見出し=タイトル、`.one` = 説明（`summary`、空なら表示しない）。開くと `.detail` に「元記事を開く（サイト名）」ボタンだけ（`<a class="src" target="_blank" rel="noopener noreferrer">`）。`href` は `http://`・`https://` で始まるときだけ設定し、そうでなければリンクにしない。文字はすべて `esc()` を通す。記事0件のときは「いまこの分野の記事はありません。」。
- [ ] **Step 4: サービス紹介のカード** — `DATA.services` から分野ごとに表示。「新着記事 ◯件」は、いま表示している対象（14日以内）の記事のうち `service` がそのサービス名のものの数。
- [ ] **Step 5: 保存機能** — 各カードに「☆ 保存」ボタン（押すと「★ 保存ずみ」、もう一度で外す）。保存すると記事の内容を localStorage `aimatome.saved.v1` に追加（同じ `url` は1件）。各分野のタブの「新着ニュース」の上に「保存した記事（◯件）」の見出しと、保存した記事のカードを出す（分野は保存時のまま、14日・8件の制限なし、「NEW」なし、日付は「2026年10月17日」形式、`price` の色付き）。保存した記事のカードにも「保存を外す」ボタン。localStorage の読み書きは `try/catch` で囲み、失敗したら画面に「この画面では保存できません」と出して、ほかの表示は続ける。
- [ ] **Step 6: バックアップ** — フッターに「保存した記事のバックアップを書き出す」「バックアップを読み込む」ボタン。書き出し: 保存した記事を `{"version":1,"articles":[...]}` のJSONファイル `ai-matome-backup-YYYYMMDD.json`（日付は書き出した日）として `Blob` でダウンロードさせ、`aimatome.lastBackup.v1` に現在時刻を保存。読み込み: ファイル選択（`<input type="file" accept=".json">`）→ `version===1` かつ `articles` が配列で、各要素に文字列の `title`・`url`（`http(s)`で始まる）・`category`（4つのどれか）があるものだけ取り込む。1件でも形が違えば**何も変えず**「このファイルは読み込めません」と表示。取り込むときは、いまの保存を消さず `url` が同じものは1件にまとめて足す。「バックアップを取りましょう」の案内: 保存が1件以上で、`lastBackup` がない、または7日以上前なら、保存した記事の見出しの下に小さく「💾 保存した記事のバックアップを、しばらく取っていません。ページの下の「バックアップを書き出す」を押してください。」を表示。
- [ ] **Step 7: フッター** — 「記事の著作権は、各サイトにあります。色は、あらかじめ決めたサービス一覧にもとづきます。料金は変わることがあるので、使う前に公式サイトで確認してください。」と、サンプルの「画面の明るさを切り替える」ボタン、更新時刻（`DATA.builtAt` を日本時間で「2026年10月17日 6:00 更新」形式）。
- [ ] **Step 8: 動作確認の準備** — 確認用に `tests/fixtures/preview_data.json`（各分野に数件、NEW対象・14日ギリギリ・説明が空・料金の色なし・`</script>` を含むタイトル・`javascript:` URLの記事を1件ずつ含む）を作り、`python -c` でこのJSONを `render_html` に通して一時フォルダに `preview.html` を作れることを `tests/test_build.py::test_render_html_with_preview_data` で確認する。期待: `python -m unittest tests.test_build -v` が PASS。

---

### Task 7: ブラウザでの見た目・動作の確認

**Files:**
- なし（確認だけ。直す点が出たら Task 6 の `template.html` を直す）

- [ ] **Step 1:** Task 6 の確認用データで作った `preview.html` を、`mcp__Claude_Browser__preview_start`（`url` に `file:///…/preview.html`）またはローカルのフォルダを開く方法でブラウザに表示する。
- [ ] **Step 2:** 次を1つずつ確認する（`read_page`／スクリーンショット）。期待どおりでなければ直して再確認:
  1. 4つのタブが切り替わり、未分類のタブにサービス紹介が出ない。
  2. 料金ボタンで絞り込める。色なしの記事は「ぜんぶ」でだけ出る。
  3. NEW は24時間以内の記事だけ。説明が空の記事でも崩れない。
  4. `</script>` を含むタイトルが文字としてそのまま表示される。`javascript:` URL の記事はリンクにならない。
  5. 「☆ 保存」→ 保存した記事の欄に出る → ページを再読み込みしても残る → 「保存を外す」で消える。
  6. バックアップを書き出し → 保存を全部外す → 読み込みで復元。壊れたJSONを読み込むと「このファイルは読み込めません」で何も変わらない。
  7. 暗い画面への切り替え、スマホ幅（`resize_window` の mobile）でタブ4つが収まる。
- [ ] **Step 3:** 結果（確認できた点・直した点）を利用者に日本語で報告する。

---

### Task 8: 自動実行（GitHub Actions）と git の準備

**Files:**
- Create: `.github/workflows/update.yml`, `.gitignore`

**Interfaces:**
- Produces: `update.yml` — 名前 `毎日の更新`。`on:` は `schedule: - cron: "0 21 * * *"`（日本時間の朝6時）、`workflow_dispatch`（手動ボタン）。`permissions:` は `contents: write`、`pages: write`、`id-token: write`。手順: `actions/checkout`（`@v4`）→ `actions/setup-python`（`@v5`、`python-version: "3.12"`）→ `python scripts/build.py` → `data/articles.json` に変更があれば `github-actions[bot]` で commit・push（`index.html` は commit しない）→ `actions/upload-pages-artifact`（`@v3`、公開用の一時フォルダ `site/` に `index.html` だけをコピーして渡す）→ `actions/deploy-pages`（`@v4`）。`concurrency: group: pages`。`build.py` が終了コード1なら、そこで失敗（＝GitHubからのメール通知）。
- Produces: `.gitignore` — `index.html`、`site/`、`__pycache__/`、`*.pyc`、`preview.html`。

- [ ] **Step 1:** 上のとおり2ファイルを作る。YAMLの書き間違いを防ぐため、`python -c "import yaml"` は使わず（部品が入っていない）、目で確認できるようインデントをそろえる。
- [ ] **Step 2:** `python scripts/build.py` を、実際のインターネットにつないだ状態で1回実行する。期待: 「読めなかったサイト」の表示（あれば）と、`index.html` と `data/articles.json` の更新。全サイト失敗なら原因（ネット接続・RSSのURL変更）を調べる。
- [ ] **Step 3:** ここで初めて `git init` を行い、`git add -A` → `git commit -m "AIニュースまとめ 初版"`（末尾に共同作成者の行を付ける）。`git status` で `index.html` が含まれない（`.gitignore` が効いている）ことを確認する。

---

### Task 9: README.md（初心者向けの使い方）

**Files:**
- Create: `README.md`

- [ ] **Step 1:** やさしい日本語で次を書く（専門用語は使うときに意味を添える）:
  1. このページの仕組み（毎朝6時に自動で記事を集めて公開）
  2. 自分のパソコンで動かして確認する方法（`python scripts/build.py` が何をするコマンドか、`index.html` をダブルクリックで開く）
  3. サービスを足す方法（`data/services.json` の各項目の意味、`free/mid/paid` の色の意味、`aliases` の使い方、書き間違えたときの直し方、例は「説明用の例」と明記）
  4. 料金の色の確認方法（サンプルの仮の値であること。公式サイトで確認して直す）
  5. 記事の元になるサイトを足す方法（`data/sources.json`。足す前にそのサイトのRSS利用条件を確認すること、`ai_only` の意味）
  6. 保存機能とバックアップの使い方（ブラウザの中だけに保存される・端末ごとに別・消えることがある・バックアップの書き出しと読み込み）
  7. 自動更新が止まったときに気づく方法（GitHubからのメール通知の確認場所と設定、Actionsの画面で手動実行する方法、60日動きがないと止まることがあること）
  8. ITmedia AI＋の利用についての注意（利用条件に「一部の抜き出し・改変の禁止」などがあり、問い合わせなしで使っていること。指摘されたら `sources.json` から外す）
  9. よくあるつまずき（記事が少ない・分野が合わない・Pythonが見つからない）
- [ ] **Step 2:** README に出てくるファイル名・コマンドが、実際にこのフォルダに存在するものか（Task 1〜8 で作ったものと一致するか）を `Glob` で確認する。期待: 食い違いなし。

---

### Task 10: 利用者のパソコンでの最終確認と公開の案内

**Files:**
- なし（作業の案内と確認）

- [ ] **Step 1:** `python -m unittest discover -s tests -v` を実行。期待: すべて PASS。
- [ ] **Step 2:** `python scripts/build.py` を実行し、できた本物の `index.html` をブラウザで開き、Task 7 の確認項目（1・2・3・5・6・7）を本物の記事で見直す。利用者にも画面を見てもらい、見た目がサンプルと同じか確認してもらう。
- [ ] **Step 3:** 利用者の OK をもらってから、GitHub への公開手順に進む。画面のどこを押すかを1つずつ案内する: GitHub のアカウント作成（利用者自身が行う。私はパスワード等を入力しない）→ 新しいリポジトリ（公開用の入れ物）の作成 → パソコンのフォルダをアップロード（`git remote add` と `git push` が何をするかを説明してから）→ Settings → Pages で「GitHub Actions」を選ぶ → Actions を手動実行して初回の公開 → 公開URLの確認 → 通知メールの設定の確認。
- [ ] **Step 4:** 公開されたページを開き、本物のURLで表示を確認して、結果を利用者に報告する。
