# 楽天ROOM 収益化自動化ツール群

楽天ROOMでの収益化を効率化するためのCLIツール集です。

1. **商品リサーチ & 投稿下書き生成** (`src/main.py`) — 売れ筋商品を自動取得し、投稿キャプション下書きを生成
2. **成果トラッキング & ダッシュボード** (`src/track_performance.py`) — アフィリエイト成果レポートを集計し、ダッシュボード化

---

# 1. 商品リサーチ & 投稿下書き生成ツール

楽天市場APIから売れ筋・レビュー評価の高い商品を自動取得し、楽天ROOM投稿用のキャプション下書きを
複数パターン自動生成するCLIツールです。

## できること / できないこと

- ✅ 楽天市場の「ランキングAPI」「商品検索API」を使った商品リサーチの自動化
- ✅ 商品情報(価格・レビュー・アフィリエイトリンク)をもとにした投稿キャプション下書きの自動生成
- ✅ CSV / Markdown での候補一覧の出力
- ❌ 楽天ROOMへの自動投稿は行いません。楽天ROOMは投稿の自動化(bot投稿)や
  フォロワー・いいねの水増しを利用規約で禁止しているため、実際の投稿は
  出力された下書きを確認・編集した上で手動で行ってください。

## セットアップ

1. [楽天ウェブサービス](https://webservice.rakuten.co.jp/) でアプリ登録し、アプリIDを取得する
   (無料・審査なしですぐ発行されます)。
2. (任意) [楽天アフィリエイト](https://affiliate.rakuten.co.jp/) に登録するとアフィリエイトIDが
   発行され、出力にアフィリエイトリンクを含められます。
3. 依存パッケージをインストール:

   ```bash
   pip install -r requirements.txt
   ```

4. `.env.example` を `.env` にコピーし、取得したIDを設定:

   ```bash
   cp .env.example .env
   # RAKUTEN_APP_ID=xxxx を編集
   ```

## 使い方

### ジャンル別ランキングから下書きを作る

```bash
python src/main.py --mode ranking --genre コスメ --period realtime --hits 10
```

`--genre` には `src/genres.yaml` に登録済みのジャンル名、または楽天のジャンルIDを直接指定できます。
ジャンルIDは [ジャンル検索API](https://webservice.rakuten.co.jp/explorer/api/IchibaGenre/Search/) で調べられます。

### キーワード検索から下書きを作る

```bash
python src/main.py --mode search --keyword "加湿器" --sort -reviewCount --min-review-count 30 --hits 10
```

### 主なオプション

| オプション | 説明 |
|---|---|
| `--mode` | `ranking`(ランキング) or `search`(キーワード検索) |
| `--genre` | ジャンル名 or ジャンルID |
| `--keyword` | 検索キーワード (`--mode search`時) |
| `--period` | ランキング期間: realtime/daily/weekly/monthly |
| `--sort` | 検索の並び順 (例: `-reviewCount`, `-reviewAverage`, `+itemPrice`) |
| `--min-price` / `--max-price` | 価格帯フィルタ |
| `--min-review-count` | このレビュー件数未満を除外 |
| `--min-review-average` | この評価未満を除外 |
| `--tags` | カンマ区切りの追加ハッシュタグ (例: `加湿器,冬支度`) |
| `--hits` | 取得件数 |

### 出力

`output/drafts_YYYYMMDD_HHMMSS.csv` と `.md` に、商品ごとに4パターンの下書き
(レビュー訴求・セール訴求・シンプル紹介・おすすめ訴求)が出力されます。
気に入った文面を選んで、楽天ROOMアプリから商品を追加する際にキャプションとして貼り付けてください。

---

# 2. 成果トラッキング & ダッシュボード生成ツール

楽天アフィリエイトの成果報酬レポートを集計し、期間別・商品別の成果推移や承認状況を
Markdown/CSV/HTMLダッシュボードとして可視化します。

## できること / できないこと

- ✅ 成果報酬レポートCSVの読み込み・集計(期間別・商品別・承認状況別)
- ✅ 前期間比の増減率算出
- ✅ Chart.jsを使ったHTMLダッシュボードの自動生成(グラフ付き)
- ❌ 楽天アフィリエイトの成果データを自動取得することはできません。
  楽天は成果レポートを取得する公開APIを提供していないため、
  [楽天アフィリエイト管理画面](https://affiliate.rakuten.co.jp/) から
  「成果報酬レポート」CSVを手動でダウンロードする必要があります。
  ダウンロード後の集計・分析・可視化はすべて自動化されます。

## 使い方

1. 楽天アフィリエイト管理画面 → レポート → 成果報酬レポートからCSVをダウンロード
2. 以下を実行:

   ```bash
   python src/track_performance.py --csv path/to/report.csv --period month --top 10
   ```

3. `output/` に以下が出力されます:
   - `performance_summary_*.md` — サマリー(累計・期間別・商品別・承認状況)
   - `performance_by_period_*.csv` — 期間別集計のCSV
   - `performance_dashboard_*.html` — グラフ付きダッシュボード(ブラウザで開く)

### 主なオプション

| オプション | 説明 |
|---|---|
| `--csv` | 楽天アフィリエイト管理画面からダウンロードしたCSVのパス(必須) |
| `--period` | 集計単位: day/week/month (デフォルト: month) |
| `--top` | 商品別ランキングの表示件数 (デフォルト: 10) |

### CSVの列名が認識されない場合

ダウンロード時期やレポート種別によってCSVの列名表記が変わることがあります。
その場合は `src/report_columns.yaml` に実際の列名を追加してください
(発生日・商品名・売上金額・成果報酬額・承認状況・数量の各項目について、
候補となる列名をリストで管理しています)。

---

## テスト

```bash
pip install -r requirements-dev.txt
pytest tests/
```
