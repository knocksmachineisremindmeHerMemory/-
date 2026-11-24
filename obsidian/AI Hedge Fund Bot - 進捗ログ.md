---
title: AI Hedge Fund Bot - 進捗ログ
date: 2026-11-24
tags: [trading, bot, hedge-fund, paper-trading, log]
status: paper-only
repo: knocksmachineisremindmeHerMemory/-
branch: claude/stoic-rubin-roi3ck
---

# AI Hedge Fund Bot - 進捗ログ

> 元資料: 「One-Person AI Hedge Fund: Setup Prompt」(2ページ)。
> 現状は **疑似取引所とテストのみ**。実取引所・実データでの検証は未実施。

## 1. セットアッププロンプトの分析
**強み**
- ペーパー取引から開始、ライブは「go live」の明示承認が条件
- 取引所側に常時ストップ(botが止まっても有効)
- 1回1%リスク、日次-3%停止、-15%キルスイッチ、レバ2倍まで
- データの厳密さ(ルックアヘッド禁止、上場廃止銘柄を含める、UTC統一)
- 「数字を捏造しない」「推定値にラベル」「最悪ケースも併記」

**弱点・リスク**
- 判定が30トレードで少ない(別の箇所は50件で食い違い)
- 7日キックオフは急ぎすぎ
- post-only指値は逆選択、ストップはtaker約定でバックテスト前提とずれる
- AIにAPIキーと発注権限が集中(プロンプトインジェクション、キー漏洩)
- キャリー・平均回帰は収益が薄い領域
- 日本在住なら取引所の利用可否と税(雑所得・総合課税)の確認が必要

## 2. 実装済み(`fund_bot/`、55テスト通過)
| 機能 | ファイル | 内容 |
|---|---|---|
| リスクルール | `risk.py` | ストップ距離から数量(口座×1%)、レバ上限、tick/step/最小注文額への丸め、日次停止、キルスイッチ、イベント前後30分禁止 |
| 疑似取引所 | `mock_exchange.py` | 約定・手数料・スリッページ・ストップ発動(ギャップは不利な価格) |
| 発注の流れ | `bot.py` | サイズ決定→エントリー→ストップ設置→1回リトライ→失敗時キャンセル+アラート。ストップ設置失敗なら即決済。`LIVE`はgo-live承認なしで起動不可 |
| 損益記録 | `bot.py` | `sync` / `close` / `add_funding`。pnl・R倍数・手数料・資金調達を `trades.csv` に記録。未確定は空欄 |
| バックテスト検証 | `backtest.py` | 次足執行、手数料・スリッページ・資金調達、ルックアヘッド検出、deflated Sharpe、買い持ち/ランダム比較、ウォークフォワード、50件未満は「偶然の域」判定 |
| 接続確認 | `check_connection.py` | テストネット限定・読み取り専用。サンドボックス、キー、時刻ずれ、残高、サブアカウント、銘柄規則、既存注文/ポジション。キーは出力しない |
| 設定 | `.gitignore`, `fund_bot/requirements.txt` | `.env.fund` を除外、ccxt指定 |

**検証方法:** ルールをわざと壊す(ミューテーション)確認を実施。日次閾値、レバ上限、手数料、ショート符号、次足執行、サンドボックス判定のいずれもテストが失敗=検出できた。

## 3. 使い方(自分の環境で)
```
pip install -r fund_bot/requirements.txt
# .env.fund に EXCHANGE_API_KEY= / EXCHANGE_API_SECRET= (chmod 600)
python -m fund_bot.check_connection --exchange bybit --env-file .env.fund \
  --symbol BTC/USDT:USDT --expect-balance 10000 --expect-account <sub-account>
```
- キーはテストネット専用、取引のみ・出金OFF・IP制限
- 出力に FAIL があればペーパー取引へ進まない

## 4. 未達・限界
- [ ] 実取引所での動作確認(ccxtの挙動は未検証)
- [ ] 実データでの検証(テストは乱数の合成データ)
- [ ] テストネット用の発注クライアント(ccxt)と `Bot` への接続
- [ ] 資金調達率の自動取得、UTC日付の自動切替
- [ ] 部分約定・追加/縮小
- [ ] プロンプト15章のフォルダ構成(`playbook.md` `calendar.md` `learning.md` など)
- 疑似取引所は「ストップが設定価格付近で約定」と楽観的に仮定

## 5. 次のアクション
1. 自分の環境で `check_connection` を実行し、出力を共有 → 調整
2. テストネット発注クライアントを作る
3. 公開の過去データを取得し、`sources.md` に出典を記録
4. 7日チェックリストに沿って雛形(playbook等)を作る

## 6. ゴールデンルール(元プロンプトより)
- ストップが取引所にない=取引しない
- コスト込みのバックテストがない=botを作らない
- 30件+のペーパー取引がバックテストと一致するまで実資金なし
- 「go live」の指示がない=ライブにしない
