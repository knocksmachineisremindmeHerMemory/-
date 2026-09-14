"""集計結果から簡易HTMLダッシュボード(Chart.js使用)を生成する。"""
from __future__ import annotations

import json
from typing import Any

_TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>楽天ROOM 成果ダッシュボード</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js"></script>
<style>
  body {{ font-family: sans-serif; margin: 2rem; background: #fafafa; color: #222; }}
  h1 {{ font-size: 1.4rem; }}
  .cards {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem; }}
  .card {{ background: white; border-radius: 8px; padding: 1rem 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,.1); min-width: 160px; }}
  .card .label {{ font-size: .8rem; color: #666; }}
  .card .value {{ font-size: 1.5rem; font-weight: bold; }}
  table {{ border-collapse: collapse; width: 100%; background: white; }}
  th, td {{ border: 1px solid #ddd; padding: .4rem .6rem; text-align: right; font-size: .85rem; }}
  th:first-child, td:first-child {{ text-align: left; }}
  section {{ margin-bottom: 2.5rem; }}
  canvas {{ max-width: 100%; background: white; border-radius: 8px; padding: 1rem; }}
</style>
</head>
<body>
<h1>楽天ROOM 成果ダッシュボード</h1>
<div class="cards">
  <div class="card"><div class="label">累計成果報酬</div><div class="value">¥{total_reward:,.0f}</div></div>
  <div class="card"><div class="label">累計売上</div><div class="value">¥{total_sales:,.0f}</div></div>
  <div class="card"><div class="label">件数</div><div class="value">{total_records}</div></div>
  <div class="card"><div class="label">前期間比</div><div class="value">{change_display}</div></div>
</div>

<section>
  <h2>期間別 成果報酬推移</h2>
  <canvas id="periodChart" height="100"></canvas>
</section>

<section>
  <h2>商品別 成果報酬 上位</h2>
  <canvas id="productChart" height="120"></canvas>
</section>

<section>
  <h2>承認状況内訳</h2>
  <table>
    <tr><th>状態</th><th>件数</th></tr>
    {status_rows}
  </table>
</section>

<script>
new Chart(document.getElementById('periodChart'), {{
  type: 'line',
  data: {{
    labels: {period_labels},
    datasets: [{{
      label: '成果報酬額',
      data: {period_rewards},
      borderColor: '#bf0000',
      backgroundColor: 'rgba(191,0,0,0.1)',
      tension: 0.2,
      fill: true,
    }}]
  }},
  options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }} }}
}});

new Chart(document.getElementById('productChart'), {{
  type: 'bar',
  data: {{
    labels: {product_labels},
    datasets: [{{
      label: '成果報酬額',
      data: {product_rewards},
      backgroundColor: '#bf0000',
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    plugins: {{ legend: {{ display: false }} }}
  }}
}});
</script>
</body>
</html>
"""


def build_dashboard_html(summary: dict[str, Any]) -> str:
    change_pct = summary.get("latest_vs_previous_pct")
    change_display = f"{change_pct:+.1f}%" if change_pct is not None else "―"

    status_rows = "\n    ".join(
        f"<tr><td>{status}</td><td>{count}</td></tr>"
        for status, count in summary.get("status_breakdown", {}).items()
    )

    by_period = summary.get("by_period", [])
    top_products = summary.get("top_products", [])

    return _TEMPLATE.format(
        total_reward=summary.get("total_reward", 0),
        total_sales=summary.get("total_sales", 0),
        total_records=summary.get("total_records", 0),
        change_display=change_display,
        status_rows=status_rows or "<tr><td>データなし</td><td>0</td></tr>",
        period_labels=json.dumps([p["period"] for p in by_period], ensure_ascii=False),
        period_rewards=json.dumps([p["reward_amount"] for p in by_period]),
        product_labels=json.dumps([p["product_name"] for p in top_products], ensure_ascii=False),
        product_rewards=json.dumps([p["reward_amount"] for p in top_products]),
    )
