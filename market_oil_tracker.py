"""
US Stock Market vs. Oil Price Tracker
Fetches daily open/close data for S&P 500, Dow Jones, NASDAQ, and WTI Crude Oil
from January 2024 to today, then generates an interactive HTML report.
"""

import json
import webbrowser
import os
from datetime import datetime

import yfinance as yf
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────
START_DATE = "2024-01-01"
END_DATE   = datetime.today().strftime("%Y-%m-%d")

TICKERS = {
    "S&P 500":   "^GSPC",
    "Dow Jones": "^DJI",
    "NASDAQ":    "^IXIC",
    "WTI Oil":   "CL=F",
}

COLORS = {
    "S&P 500":   "#4e9af1",
    "Dow Jones": "#f1c84e",
    "NASDAQ":    "#a084e8",
    "WTI Oil":   "#e8734a",
}

# ── Fetch data (one ticker at a time to avoid lock contention) ────────────────
import time

print("Fetching data from Yahoo Finance…")
series = {}
for name, ticker in TICKERS.items():
    for attempt in range(3):
        try:
            df = yf.download(
                ticker,
                start=START_DATE,
                end=END_DATE,
                auto_adjust=True,
                progress=False,
            )
            if df.empty:
                raise ValueError("empty response")
            # yfinance may return multi-level columns for a single ticker
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df[["Open", "Close"]].rename(columns={"Open": "open", "Close": "close"}).dropna()
            df["pct_change"] = df["close"].pct_change() * 100
            df.index = pd.to_datetime(df.index)
            series[name] = df
            print(f"  {name}: {len(df)} trading days loaded")
            break
        except Exception as exc:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"  WARNING – could not load {name}: {exc}")

# ── Correlation table (daily % change vs WTI Oil) ─────────────────────────────
oil_pct = series["WTI Oil"]["pct_change"].rename("oil")
corr_rows = []
for name in ["S&P 500", "Dow Jones", "NASDAQ"]:
    merged = pd.concat([series[name]["pct_change"], oil_pct], axis=1).dropna()
    merged.columns = ["market", "oil"]
    corr = merged["market"].corr(merged["oil"])
    corr_rows.append({"index": name, "correlation": round(corr, 4), "n": len(merged)})

# ── Build JSON for chart.js ───────────────────────────────────────────────────
def df_to_json(df, key):
    return [
        {"x": str(idx.date()), "y": round(float(val), 4)}
        for idx, val in df[key].items()
        if pd.notna(val)
    ]

chart_data = {}
for name, df in series.items():
    chart_data[name] = {
        "close":      df_to_json(df, "close"),
        "pct_change": df_to_json(df, "pct_change"),
    }

# Scatter: oil % change (x) vs market % change (y) per index
scatter_data = {}
for name in ["S&P 500", "Dow Jones", "NASDAQ"]:
    merged = pd.concat([
        series[name]["pct_change"].rename("market"),
        series[name]["close"].rename("close"),
        oil_pct,
    ], axis=1).dropna()
    scatter_data[name] = [
        {
            "x":     round(float(row["oil"]), 3),
            "y":     round(float(row["market"]), 3),
            "date":  str(d.date()),
            "close": round(float(row["close"]), 2),
        }
        for d, row in merged.iterrows()
    ]

# ── Generate HTML ─────────────────────────────────────────────────────────────
chart_data_json   = json.dumps(chart_data)
scatter_data_json = json.dumps(scatter_data)
corr_json         = json.dumps(corr_rows)
colors_json       = json.dumps(COLORS)
start_label       = START_DATE
end_label         = END_DATE

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>US Markets vs. Oil Price</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0;}}
    body{{font-family:'Segoe UI',sans-serif;background:#0d1117;color:#e6edf3;min-height:100vh;padding:32px 16px;}}
    h1{{font-size:1.7rem;text-align:center;color:#58a6ff;margin-bottom:6px;letter-spacing:.04em;}}
    .subtitle{{text-align:center;color:#8b949e;font-size:.9rem;margin-bottom:36px;}}
    .section-title{{font-size:1.1rem;color:#79c0ff;margin-bottom:16px;border-bottom:1px solid #21262d;padding-bottom:8px;}}
    .card{{background:#161b22;border:1px solid #21262d;border-radius:12px;padding:24px;max-width:1100px;margin:0 auto 32px;}}
    .tabs{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap;}}
    .tab-btn{{padding:8px 16px;border-radius:6px;border:1px solid #30363d;background:#21262d;color:#c9d1d9;
              cursor:pointer;font-size:.85rem;font-weight:600;transition:all .2s;}}
    .tab-btn.active,.tab-btn:hover{{background:#1f6feb;border-color:#1f6feb;color:#fff;}}
    canvas{{max-width:100%;}}
    .corr-table{{width:100%;border-collapse:collapse;font-size:.9rem;}}
    .corr-table th{{text-align:left;padding:10px 12px;border-bottom:1px solid #30363d;color:#8b949e;font-weight:600;}}
    .corr-table td{{padding:10px 12px;color:#e6edf3;}}
    .corr-table tr+tr td{{border-top:1px solid #21262d;}}
    .corr-bar-bg{{background:#21262d;border-radius:4px;height:10px;width:200px;display:inline-block;vertical-align:middle;margin-left:10px;}}
    .corr-bar{{height:10px;border-radius:4px;display:inline-block;}}
    .pill{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:.8rem;font-weight:700;}}
    .pill.pos{{background:#0d4429;color:#3fb950;}}
    .pill.neg{{background:#3d1c1c;color:#f85149;}}
    .legend-row{{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:14px;}}
    .legend-item{{display:flex;align-items:center;gap:6px;font-size:.82rem;color:#8b949e;}}
    .legend-dot{{width:12px;height:12px;border-radius:50%;flex-shrink:0;}}
    .note{{font-size:.78rem;color:#484f58;margin-top:10px;}}
    @media(max-width:600px){{.corr-bar-bg{{width:80px;}}}}
  </style>
</head>
<body>

<h1>US Markets vs. Oil Price</h1>
<p class="subtitle">Daily open &amp; close data &mdash; {start_label} through {end_label}</p>

<!-- ── Tab 1: Price History ───────────────────────────────────────────────── -->
<div class="card">
  <div class="section-title">Daily Closing Price</div>
  <div class="tabs" id="priceTabs">
    <button class="tab-btn active" onclick="showPrice('S&P 500',this)">S&amp;P 500</button>
    <button class="tab-btn" onclick="showPrice('Dow Jones',this)">Dow Jones</button>
    <button class="tab-btn" onclick="showPrice('NASDAQ',this)">NASDAQ</button>
    <button class="tab-btn" onclick="showPrice('WTI Oil',this)">WTI Oil (USD/bbl)</button>
  </div>
  <canvas id="priceChart" height="90"></canvas>
</div>

<!-- ── Tab 2: Daily % Change ─────────────────────────────────────────────── -->
<div class="card">
  <div class="section-title">Daily % Change — Markets vs. Oil</div>
  <div class="legend-row" id="pctLegend"></div>
  <canvas id="pctChart" height="100"></canvas>
  <p class="note">Lines show each index's daily % change. WTI Oil is the dashed orange line.</p>
</div>

<!-- ── Tab 3: Scatter ────────────────────────────────────────────────────── -->
<div class="card">
  <div class="section-title">Oil % Change vs. Market % Change (Scatter)</div>
  <div class="tabs" id="scatterTabs">
    <button class="tab-btn active" onclick="showScatter('S&P 500',this)">S&amp;P 500</button>
    <button class="tab-btn" onclick="showScatter('Dow Jones',this)">Dow Jones</button>
    <button class="tab-btn" onclick="showScatter('NASDAQ',this)">NASDAQ</button>
  </div>
  <canvas id="scatterChart" height="90"></canvas>
  <p class="note">Each dot = one trading day. X-axis = WTI oil daily % change; Y-axis = index daily % change.</p>
</div>

<!-- ── Correlation Table ─────────────────────────────────────────────────── -->
<div class="card">
  <div class="section-title">Pearson Correlation: Daily % Change (Market vs. WTI Oil)</div>
  <table class="corr-table" id="corrTable"></table>
  <p class="note">Correlation ranges from &minus;1 (perfect inverse) to +1 (perfect positive). Values near 0 indicate little linear relationship.</p>
</div>

<script>
const DATA   = {chart_data_json};
const SDATA  = {scatter_data_json};
const CORR   = {corr_json};
const COLORS = {colors_json};

// ── Price chart ──────────────────────────────────────────────────────────────
let priceChart = null;
function showPrice(name, btn) {{
  document.querySelectorAll('#priceTabs .tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const pts = DATA[name].close;
  const color = COLORS[name];
  if (priceChart) {{
    priceChart.data.datasets[0].data  = pts;
    priceChart.data.datasets[0].label = name;
    priceChart.data.datasets[0].borderColor = color;
    priceChart.data.datasets[0].backgroundColor = color + '22';
    priceChart.update();
    return;
  }}
  const ctx = document.getElementById('priceChart').getContext('2d');
  priceChart = new Chart(ctx, {{
    type: 'line',
    data: {{ datasets: [{{ label: name, data: pts, borderColor: color,
      backgroundColor: color + '22', borderWidth: 2, pointRadius: 0, fill: true,
      tension: 0.1 }}] }},
    options: {{
      responsive: true,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{ legend: {{ display: false }},
        tooltip: {{ callbacks: {{
          label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toLocaleString(undefined,{{minimumFractionDigits:2,maximumFractionDigits:2}})}}`
        }} }} }},
      scales: {{
        x: {{ type: 'time', time: {{ unit: 'month' }}, ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
        y: {{ ticks: {{ color: '#8b949e', callback: v => v.toLocaleString() }}, grid: {{ color: '#21262d' }} }}
      }}
    }}
  }});
}}

// ── % Change chart ───────────────────────────────────────────────────────────
(function buildPctChart() {{
  const indices = ['S&P 500','Dow Jones','NASDAQ'];
  const lineColors = {{ 'S&P 500': '#4e9af1', 'Dow Jones': '#f1c84e', 'NASDAQ': '#a084e8' }};

  const legendEl = document.getElementById('pctLegend');
  [...indices, 'WTI Oil'].forEach(n => {{
    legendEl.innerHTML += `<div class="legend-item"><div class="legend-dot" style="background:${{COLORS[n]}}"></div>${{n}}</div>`;
  }});

  const datasets = indices.map((name, i) => ({{
    type: 'line',
    label: name,
    data: DATA[name].pct_change,
    borderColor: lineColors[name],
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    pointRadius: 0,
    tension: 0.1,
    order: i + 1,
  }}));

  datasets.push({{
    type: 'line',
    label: 'WTI Oil',
    data: DATA['WTI Oil'].pct_change,
    borderColor: COLORS['WTI Oil'],
    backgroundColor: 'transparent',
    borderWidth: 2.5,
    borderDash: [4, 3],
    pointRadius: 0,
    tension: 0.1,
    order: 0,
  }});

  const ctx = document.getElementById('pctChart').getContext('2d');
  new Chart(ctx, {{
    type: 'line',
    data: {{ datasets }},
    options: {{
      responsive: true,
      interaction: {{ mode: 'index', intersect: false }},
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{
          label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y >= 0 ? '+' : ''}}${{ctx.parsed.y.toFixed(2)}}%`
        }} }}
      }},
      scales: {{
        x: {{ type: 'time', time: {{ unit: 'month' }}, ticks: {{ color: '#8b949e' }}, grid: {{ color: '#21262d' }} }},
        y: {{ ticks: {{ color: '#8b949e', callback: v => (v>0?'+':'')+v.toFixed(1)+'%' }}, grid: {{ color: '#21262d' }} }}
      }}
    }}
  }});
}})();

// ── Scatter chart ─────────────────────────────────────────────────────────────
let scatterChart = null;
function showScatter(name, btn) {{
  document.querySelectorAll('#scatterTabs .tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const pts = SDATA[name];
  const color = COLORS[name];
  if (scatterChart) {{
    scatterChart.data.datasets[0].data  = pts;
    scatterChart.data.datasets[0].label = name;
    scatterChart.data.datasets[0].backgroundColor = color + '88';
    scatterChart.data.datasets[0].borderColor      = color;
    scatterChart.update();
    return;
  }}
  const ctx = document.getElementById('scatterChart').getContext('2d');
  scatterChart = new Chart(ctx, {{
    type: 'scatter',
    data: {{ datasets: [{{
      label: name,
      data: pts,
      backgroundColor: color + '88',
      borderColor: color,
      borderWidth: 1,
      pointRadius: 4,
      pointHoverRadius: 6,
    }}] }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{ callbacks: {{
          label: ctx => {{
            const d = ctx.raw;
            return [`${{d.date}}`, `Oil: ${{d.x>=0?'+':''}}${{d.x}}%  ${{name}}: ${{d.y>=0?'+':''}}${{d.y}}%`];
          }}
        }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'WTI Oil Daily % Change', color: '#8b949e' }},
             ticks: {{ color: '#8b949e', callback: v => (v>0?'+':'')+v+'%' }},
             grid: {{ color: '#21262d' }} }},
        y: {{ title: {{ display: true, text: name + ' Daily % Change', color: '#8b949e' }},
             ticks: {{ color: '#8b949e', callback: v => (v>0?'+':'')+v+'%' }},
             grid: {{ color: '#21262d' }} }}
      }}
    }}
  }});
}}

// ── Correlation table ─────────────────────────────────────────────────────────
(function buildCorrTable() {{
  const t = document.getElementById('corrTable');
  t.innerHTML = `<thead><tr><th>Index</th><th>Correlation with WTI Oil</th><th>Trading Days</th><th>Interpretation</th></tr></thead><tbody></tbody>`;
  const body = t.querySelector('tbody');
  CORR.forEach(row => {{
    const c = row.correlation;
    const abs = Math.abs(c);
    const pos = c >= 0;
    const barW = Math.round(abs * 100);
    const barColor = pos ? '#3fb950' : '#f85149';
    let label = abs < 0.1 ? 'Very weak' : abs < 0.3 ? 'Weak' : abs < 0.5 ? 'Moderate' : abs < 0.7 ? 'Strong' : 'Very strong';
    label += pos ? ' positive' : ' negative';
    const pill = pos
      ? `<span class="pill pos">+${{c}}</span>`
      : `<span class="pill neg">${{c}}</span>`;
    body.innerHTML += `<tr>
      <td style="color:${{COLORS[row.index]}};font-weight:700">${{row.index}}</td>
      <td>${{pill}} <span class="corr-bar-bg"><span class="corr-bar" style="width:${{barW}}%;background:${{barColor}}"></span></span></td>
      <td style="color:#8b949e">${{row.n}}</td>
      <td style="color:#8b949e;font-size:.82rem">${{label}}</td>
    </tr>`;
  }});
}})();

// ── Init ──────────────────────────────────────────────────────────────────────
showPrice('S&P 500', document.querySelector('#priceTabs .tab-btn'));
showScatter('S&P 500', document.querySelector('#scatterTabs .tab-btn'));
</script>
</body>
</html>
"""

output_path = os.path.expanduser("~/market_oil_report.html")
with open(output_path, "w") as f:
    f.write(html)

print(f"\nReport saved to: {output_path}")
print("Opening in browser…")
webbrowser.open(f"file://{output_path}")
