"""04 図（PNG、日付などのメタデータは入れない）。都道府県は北から南の順に並べる。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：総務省・経済産業省「経済センサス」（2009・2014・2024年 基礎調査、2016・2021年 活動調査）、総務省「人口推計」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
nat = pd.read_csv(R / "national.csv").set_index("year")
pr = pd.read_csv(R / "pref_2009_2024.csv", dtype={"pref_code": str}).set_index("pref_code").sort_index()
REG = ["北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
RC = dict(zip(REG, [C[0], C[1], C[2], C[3], C[4], C[5], "#d38bb0", "#4fa3a5"]))

# 図1 全国の推移（2009年＝100）
fig, ax = plt.subplots(figsize=(8.8, 5.2))
yrs = nat.index.values
for col, lab, c in [("offices_62", "銀行業の事業所数", C[0]), ("offices_63", "協同組織金融業（信用金庫・信用組合など）の事業所数", C[2]),
                    ("workers_62", "銀行業の従業者数", C[0]), ("pop_k", "人口", C[5])]:
    v = nat[col] / nat.loc[2009, col] * 100
    ax.plot(yrs, v, marker="o", ms=5, lw=2 if col != "workers_62" else 1.3, color=c, ls="--" if col == "workers_62" else "-", label=lab)
    ax.annotate(f"{v.iloc[-1]:.1f}", (2024, v.iloc[-1]), xytext=(2024.3, v.iloc[-1]), fontsize=9, va="center", color=c)
ax.set_xticks(yrs); ax.set_xticklabels([f"{y}年\n{nat.loc[y, 'survey']}" for y in yrs], fontsize=9)
ax.set_xlim(2008.3, 2025.6); ax.set_ylim(78, 104)
ax.set_ylabel("2009年＝100")
ax.legend(frameon=False, loc="lower left", fontsize=8.8)
style(ax)
ax.set_title(f"銀行業の事業所は2009年の{m['nat_offices_62']['2009']:,}から2024年の{m['nat_offices_62']['2024']:,}へ（{m['nat_change_62_2009_2024_pct']:.1f}%）", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.08, right=0.97, top=0.92, bottom=0.17)
save(fig, F / "fig1_national_trend.png", SRC, note="民営事業所。銀行業は日本銀行を含む。基礎調査と活動調査は調査の方法が違う")

# 図2 都道府県別の増減率（北から南）
fig, ax = plt.subplots(figsize=(8.8, 9.4))
y = np.arange(len(pr))[::-1]
ax.barh(y, pr["change_pct"], color=[RC[r] for r in pr["region"]], height=0.72)
for yy, v in zip(y, pr["change_pct"]):
    ax.text(v - 0.6, yy, f"{v:.1f}", va="center", ha="right", fontsize=7.6, color=INK2)
ax.set_yticks(y); ax.set_yticklabels(pr["pref"], fontsize=8.4)
ax.axvline(0, color=INK2, lw=0.8)
ax.axvline(m["nat_change_62_2009_2024_pct"], color=INK, lw=0.9, ls="--")
ax.text(m["nat_change_62_2009_2024_pct"] + 0.5, y[0] + 0.9, f"全国 {m['nat_change_62_2009_2024_pct']:.1f}%", fontsize=8.6)
ax.set_xlim(-66, 3); ax.set_ylim(-1, len(pr) + 0.8)
ax.set_xlabel("銀行業の事業所数の増減率（2009→2024年、%）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=RC[r], label=r) for r in REG], frameon=False, loc="lower left", fontsize=8.4, ncol=2)
ax.set_title(f"47都道府県のすべてで減った（北から南の順。中央値は{m['pref_change_median_pct']:.1f}%）", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.13, right=0.97, top=0.95, bottom=0.08)
save(fig, F / "fig2_pref_change.png", SRC)

# 図3 人口の増減率と事業所の増減率
fig, ax = plt.subplots(figsize=(8.8, 5.6))
for rg in REG:
    g = pr[pr.region == rg]
    ax.scatter(g["pop_change_pct"], g["change_pct"], s=34, color=RC[rg], label=rg, alpha=0.9, edgecolor="white", lw=0.5)
xs = np.linspace(pr["pop_change_pct"].min() - 1, pr["pop_change_pct"].max() + 1, 10)
ax.plot(xs, m["intercept_offices_on_pop"] + m["slope_offices_on_pop"] * xs, color=INK2, lw=1, ls="--")
for code in ["13", "15"]:          # 本文で例に挙げた県だけ（減り方の大きい県は名指ししない）
    ax.annotate(pr.loc[code, "pref"], (pr.loc[code, "pop_change_pct"], pr.loc[code, "change_pct"]), xytext=(4, 3), textcoords="offset points", fontsize=8.4)
ax.axhline(0, color=INK2, lw=0.6); ax.axvline(0, color=INK2, lw=0.6)
ax.set_xlabel("人口の増減率（2009→2024年、%）"); ax.set_ylabel("銀行業の事業所数の増減率（%）")
ax.legend(frameon=False, loc="lower right", fontsize=8.2, ncol=2)
style(ax)
ax.set_title(f"人口が減った県ほど事業所も減ったが、関係は弱い（相関係数 {m['corr_pop_offices']:.3f}）", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.09, right=0.97, top=0.92, bottom=0.14)
save(fig, F / "fig3_pop_vs_change.png", SRC, note="点は都道府県。破線は回帰直線。名前は本文で例に挙げた県だけ付けた。各県の値は図2（北から南の順）")

# 図4 問い直し：地方別の、1年あたりの増減率（2016年の前と後）
rg = pd.DataFrame(q["region"]).T.reindex(REG)
fig, ax = plt.subplots(figsize=(8.8, 5.2))
x = np.arange(len(REG)); w = 0.38
ax.bar(x - w / 2, rg["pct_per_year_2009_2016"], w, color=C[5], label="2009→2016年")
ax.bar(x + w / 2, rg["pct_per_year_2016_2024"], w, color=C[0], label="2016→2024年")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(x); ax.set_xticklabels(REG)
ax.set_ylabel("1年あたりの増減率（%）")
ax.legend(frameon=False, loc="lower left", fontsize=9)
style(ax)
ax.set_title(f"北海道を除く7地方で、2016年以降に減り方が速くなった（全国 {q['nat_pct_per_year']['2009_2016']:.2f}%→{q['nat_pct_per_year']['2016_2024']:.2f}%／年）", loc="left", fontsize=11)
fig.subplots_adjust(left=0.09, right=0.97, top=0.92, bottom=0.12)
save(fig, F / "fig4_region_timing.png", SRC, note="増減率を年数で割った値（単純平均）")
