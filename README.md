# 楽天ROOM 商品リサーチ & 投稿下書き生成ツール

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

## テスト

```bash
pip install -r requirements-dev.txt
pytest tests/
```
