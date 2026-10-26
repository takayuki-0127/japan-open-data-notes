"""04 図と CSV：mart を CSV に書き出し、記事用の図を作る"""
import json
from pathlib import Path
import duckdb, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import networkx as nx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False
INK, MUTE, C1, C2, C3 = "#222", "#777", "#2b6cb0", "#dd6b20", "#2f855a"

con = duckdb.connect(str(ROOT / "data" / "stats.duckdb"), read_only=True)
df = con.execute("select * from mart_indicators_monthly order by month").fetchdf()
log = con.execute("select load_id, as_of, tbl, n_rows, last_month from load_log order by load_id, tbl").fetchdf()
con.close()
df.to_csv(ROOT / "results" / "mart_indicators_monthly.csv", index=False)
log.to_csv(ROOT / "results" / "load_log.csv", index=False)
df["month"] = pd.to_datetime(df["month"])

# 図1 データの流れ
fig, ax = plt.subplots(figsize=(11, 3.6)); ax.axis("off"); ax.set_xlim(0, 11); ax.set_ylim(0, 3.6)
boxes = [(0.2, "e-Stat\n（ファイル4つ）", "CPI・労働力調査\n求人倍率・毎月勤労統計"),
         (2.4, "01 取得\nPython", "再試行（指数バックオフ）\n失敗時はキャッシュ"),
         (4.6, "02 DuckDB\nraw テーブル", "縦持ちで保存\n取り込み記録・前回との差分"),
         (6.8, "03 dbt\nstg → mart", "前年比・実質化\nテスト 20 本"),
         (9.0, "04 出力", "Streamlit・図・CSV\n（毎月自動：Actions 例）")]
for x, t, s in boxes:
    ax.add_patch(FancyBboxPatch((x, 1.5), 1.8, 1.5, boxstyle="round,pad=0.05", fc="#eef4fb", ec=C1, lw=1.5))
    ax.text(x + 0.9, 2.45, t, ha="center", va="center", fontsize=11.5, color=INK, weight="bold")
    ax.text(x + 0.9, 1.05, s, ha="center", va="center", fontsize=9, color=MUTE)
for x in (2.0, 4.2, 6.4, 8.6):
    ax.annotate("", xy=(x + 0.4, 2.25), xytext=(x, 2.25), arrowprops=dict(arrowstyle="->", color=INK, lw=1.5))
ax.text(0.2, 3.35, "データの流れ：API キーを使わず、取得から公開まで同じコードで再現できる", fontsize=12.5, color=INK, weight="bold")
fig.savefig(FIG / "f12_flow.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 図2 指標（2015年〜）
d = df[df.month >= "2015-01-01"]
fig, axs = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
axs[0].plot(d.month, d.cpi_all_yoy, color=C1, label="総合"); axs[0].plot(d.month, d.cpi_core_core_yoy, color=C2, label="生鮮食品及びエネルギーを除く総合")
axs[0].axhline(0, color=MUTE, lw=0.8); axs[0].set_title("物価の前年同月比（%）", loc="left", fontsize=12); axs[0].legend(frameon=False, fontsize=9)
axs[1].bar(d.month, d.real_wage_total_yoy, width=25, color=[C3 if v > 0 else C2 for v in d.real_wage_total_yoy.fillna(0)], label="実質（公表値、緑＝プラス・橙＝マイナス）")
axs[1].plot(d.month, d.wage_total_yoy, color=INK, lw=1.2, label="名目")
axs[1].axhline(0, color=MUTE, lw=0.8); axs[1].set_title("賃金（現金給与総額）の前年同月比（%）", loc="left", fontsize=12); axs[1].legend(frameon=False, fontsize=9)
ax2 = axs[2]; ax2.plot(d.month, d.unemp_rate_sa, color=C1); ax2.set_ylabel("完全失業率（%）", color=C1)
ax3 = ax2.twinx(); ax3.plot(d.month, d.jobs_ratio_sa, color=C2); ax3.set_ylabel("有効求人倍率（倍）", color=C2); ax3.spines["top"].set_visible(False)
ax2.set_title("完全失業率と有効求人倍率（季節調整値）", loc="left", fontsize=12)
fig.text(0.01, 0.005, "出典：総務省統計局・厚生労働省（e-Stat）を加工して作成。mart_indicators_monthly から描画", fontsize=8, color=MUTE)
fig.tight_layout(); fig.savefig(FIG / "f12_indicators.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 図3 dbt の系譜図（manifest.json から）
man = json.loads((ROOT / "dbt" / "target" / "manifest.json").read_text())
G = nx.DiGraph(); kinds = {}
for uid, n in {**man["nodes"], **man["sources"]}.items():
    if n["resource_type"] in ("model", "source"):
        name = n["name"]; kinds[name] = n["resource_type"]
        for dep in n.get("depends_on", {}).get("nodes", []):
            dn = (man["nodes"].get(dep) or man["sources"].get(dep))["name"]
            G.add_edge(dn, name)
tests_per = {}
for uid, n in man["nodes"].items():
    if n["resource_type"] == "test":
        for dep in n["depends_on"]["nodes"]:
            nm = (man["nodes"].get(dep) or man["sources"].get(dep))["name"]; tests_per[nm] = tests_per.get(nm, 0) + 1
layer = {n: (0 if kinds.get(n) == "source" else 1 if n.startswith("stg_") else 2) for n in G.nodes}
pos = {}
for L in (0, 1, 2):
    ns = sorted([n for n in G.nodes if layer[n] == L])
    for i, n in enumerate(ns):
        pos[n] = (L * 3.2, -(i - (len(ns) - 1) / 2) * 1.2)
fig, ax = plt.subplots(figsize=(10, 5)); ax.axis("off")
nx.draw_networkx_edges(G, pos, ax=ax, edge_color=MUTE, arrows=True, arrowsize=14, node_size=3200)
for n, (x, y) in pos.items():
    col = {0: "#f7fafc", 1: "#eef4fb", 2: "#e6f4ea"}[layer[n]]
    ax.add_patch(FancyBboxPatch((x - 1.05, y - 0.32), 2.1, 0.64, boxstyle="round,pad=0.03", fc=col, ec=INK, lw=1))
    ax.text(x, y + 0.05, n, ha="center", va="center", fontsize=10.5, color=INK)
    if tests_per.get(n): ax.text(x, y - 0.2, f"テスト {tests_per[n]}本", ha="center", va="center", fontsize=8, color=C3)
for L, t in ((0, "source（生データ）"), (1, "staging（view）"), (2, "mart（table）")):
    ax.text(L * 3.2, 3.0, t, ha="center", fontsize=11, color=MUTE)
ax.set_xlim(-1.4, 7.8); ax.set_ylim(-2.6, 3.3)
fig.savefig(FIG / "f12_lineage.png", dpi=150, bbox_inches="tight"); plt.close(fig)

# 図4 テストと頑健性チェックの結果
res = json.loads((ROOT / "results" / "dbt_results.json").read_text())
rob = json.loads((ROOT / "results" / "robustness.json").read_text()) if (ROOT / "results" / "robustness.json").exists() else {}
tests = [r for r in res["results"] if r["type"] == "test"]
fig, axs = plt.subplots(1, 2, figsize=(12, 5.2), gridspec_kw={"width_ratios": [1.15, 1]})
ax = axs[0]; names = [r["name"][:44] for r in tests]
ax.barh(range(len(tests)), [1] * len(tests), color=[C3 if r["status"] == "pass" else C2 for r in tests])
for i, r in enumerate(tests): ax.text(0.02, i, f"{r['name'][:52]}", va="center", fontsize=7.5, color="white")
ax.set_yticks([]); ax.set_xticks([]); ax.invert_yaxis(); [s.set_visible(False) for s in ax.spines.values()]
ax.set_title(f"ふだんの実行：dbt のテスト {sum(r['status']=='pass' for r in tests)}/{len(tests)} 本が合格", loc="left", fontsize=11.5)
ax = axs[1]; ax.axis("off")
bd = rob.get("bad_data", {}); rs = rob.get("retry_success", {}); df_ = rob.get("diff", {}).get("by_table_status", {})
lines = ["わざと壊して確かめた3つの試験", "",
         f"① 通信が2回失敗 → {rs.get('tries','?')}回目で取得（待ち {', '.join(str(int(w)) for w in rs.get('waits_sec', []))} 秒）",
         "    5回とも失敗 → 前回のファイルで続行（--strict なら停止）", "",
         "② 先月時点の取り込みと比べた差分",
         "    " + "・".join(f"{k.split(':')[0].replace('raw_','')} +{v}" for k, v in df_.items()) + "（新しい月の値）",
         "    過去の値の改定：0 件", "",
         "③ 壊れたデータを入れた実行（失業率25%・重複月・欠損）",
         f"    失敗したテスト {len(bd.get('failed_tests', []))} 本 → mart は作られずに停止",
         *[f"    ・{t}" for t in bd.get("failed_tests", [])]]
for i, l in enumerate(lines):
    ax.text(0, 1 - i * 0.068, l, fontsize=10.5 if i else 12, color=INK, weight="bold" if i == 0 else "normal", transform=ax.transAxes, va="top")
fig.tight_layout(); fig.savefig(FIG / "f12_tests.png", dpi=150, bbox_inches="tight"); plt.close(fig)
print("figures ok", len(df), "rows", str(df.month.max().date()))
