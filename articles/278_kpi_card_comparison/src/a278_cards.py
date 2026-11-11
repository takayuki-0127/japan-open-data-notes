"""KPI カードの矢印（良い／悪い）を、前月比・前年同月比・目標比で判定して食い違いを数える"""
import json, duckdb, numpy as np, pandas as pd, matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from common import DATA, SQL, RES, save, tsql_to_duckdb, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
df = pd.read_csv(DATA / "kpi_monthly.csv")
con = duckdb.connect()
con.register("kpi_monthly", df)
q = tsql_to_duckdb((SQL / "01_card_status.sql").read_text()).replace("dbo.", "")
st = con.execute(q).df().sort_values(["kpi", "ym"]).reset_index(drop=True)
# 照合：pandas で独立に計算した判定と一致するか
chk = []
for k, g in df.groupby("kpi"):
    g = g.sort_values("ym"); d = g["direction"].iloc[0]
    mom = np.sign((g["value"] - g["value"].shift(1)) * d); yoy = np.sign((g["value"] - g["value"].shift(12)) * d)
    tg = np.where((g["value"] - g["target"]) * d >= 0, 1, -1)
    chk.append(pd.DataFrame({"kpi": k, "ym": g["ym"], "m": mom.replace(0, -1), "y": yoy.replace(0, -1), "t": tg}))
chk = pd.concat(chk).sort_values(["kpi", "ym"]).reset_index(drop=True)
w = st[st["ym"] >= "2024-01"].merge(chk, on=["kpi", "ym"])
assert (w["good_mom"] == w["m"]).all() and (w["good_yoy"] == w["y"]).all() and (w["good_target"] == w["t"]).all()
# 季節の強さ：月のダミーで説明できる分散の割合（2023〜2025年、伸びを除いてから）
def season_share(g):
    v = np.log(g["value"].to_numpy()); t = np.arange(len(v)); v = v - np.polyval(np.polyfit(t, v, 1), t)
    mo = pd.Series(v).groupby(t % 12).transform("mean").to_numpy()
    return float(1 - ((v - mo) ** 2).sum() / ((v - v.mean()) ** 2).sum())
ss = {k: season_share(g.sort_values("ym")) for k, g in df.groupby("kpi")}
per = w.groupby("kpi").apply(lambda g: pd.Series({
    "mom_vs_yoy": float((g.good_mom != g.good_yoy).mean()), "mom_vs_target": float((g.good_mom != g.good_target).mean()),
    "yoy_vs_target": float((g.good_yoy != g.good_target).mean())})).reset_index()
per["season_share"] = per["kpi"].map(ss)
per = per.sort_values("season_share", ascending=False)
per.to_csv(RES / "disagreement_by_kpi.csv", index=False)
cells = len(w)
tot = {c: float((w["good_mom"] != w[c2]).mean()) for c, c2 in [("mom_vs_yoy", "good_yoy"), ("mom_vs_target", "good_target")]}
tot["yoy_vs_target"] = float((w["good_yoy"] != w["good_target"]).mean())
strong = per.iloc[:5]; weak = per.iloc[5:]  # 季節の強さの上位5と下位5
both = w[(w.good_yoy == 1) & (w.good_target == -1)]
res = {"cells": cells, "kpis": int(w.kpi.nunique()), "months": int(w.ym.nunique()), "rates": tot,
       "mom_vs_yoy_strong_season": float(strong.mom_vs_yoy.mean()), "mom_vs_yoy_weak_season": float(weak.mom_vs_yoy.mean()),
       "n_strong": len(strong), "n_weak": len(weak),
       "yoy_good_target_bad": int(len(both)), "yoy_bad_target_good": int(((w.good_yoy == -1) & (w.good_target == 1)).sum()),
       "sql_matches_pandas": True,
       "corr_season_vs_mom_yoy": float(np.corrcoef(per.season_share, per.mom_vs_yoy)[0, 1])}
# 例のカード：前月比は良いのに前年同月比・目標比は悪い、季節の強い KPI の月
ex = w[(w.good_mom == 1) & (w.good_yoy == -1) & (w.good_target == -1)].merge(per[["kpi", "season_share"]], on="kpi")
ex = ex.sort_values(["season_share", "ym"], ascending=[False, False]).iloc[0]
e = df[(df.kpi == ex.kpi)].set_index("ym")
cur = e.loc[ex.ym]; pm = e["value"].shift(1).loc[ex.ym]; py = e["value"].shift(12).loc[ex.ym]
res["example"] = {"kpi": ex.kpi, "ym": ex.ym, "value": float(cur.value), "prev_month": float(pm), "prev_year": float(py), "target": float(cur.target)}
json.dump(res, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# 図1：同じ月の3つのカード
def pct(a, b): return (a / b - 1) * 100
fig, axs = plt.subplots(1, 3, figsize=(11, 3.4))
u = cur.unit
cards = [("A：前月比だけ", [(f"前月比 {pct(cur.value, pm):+.1f}%", GREEN)]),
         ("B：前年同月比だけ", [(f"前年同月比 {pct(cur.value, py):+.1f}%", ORANGE)]),
         ("C：目標比＋前年同月比", [(f"目標比 {pct(cur.value, cur.target):+.1f}%", ORANGE), (f"前年同月比 {pct(cur.value, py):+.1f}%", ORANGE)])]
for ax, (ttl, lines) in zip(axs, cards):
    ax.set_axis_off(); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.add_patch(FancyBboxPatch((0.03, 0.05), 0.94, 0.85, boxstyle="round,pad=0.02", fc="white", ec=GRAY, lw=1.2))
    ax.text(0.5, 0.97, ttl, ha="center", va="bottom", fontsize=11, color=INK)
    ax.text(0.1, 0.75, f"{ex.kpi}（{ex.ym}）", fontsize=10, color=GRAY)
    ax.text(0.1, 0.52, f"{cur.value:,.1f} {u}", fontsize=20, color=INK, weight="bold")
    for i, (s, c) in enumerate(lines):
        mark = "▲ 良い" if c == GREEN else "▼ 悪い"
        ax.text(0.1, 0.32 - i * 0.15, f"{s}　{mark}", fontsize=10.5, color=c)
fig.suptitle("同じ月・同じ数字でも、比べる相手で「良い／悪い」が逆になる", y=1.08, fontsize=12)
save(fig, "a278_cards.png", y=-0.03)

# 図2：KPI ごとの食い違いの割合（季節の強い順）
fig, ax = plt.subplots(figsize=(8.5, 4.6))
y = np.arange(len(per))
ax.barh(y - 0.2, per.mom_vs_yoy * 100, 0.38, color=BLUE, label="前月比 と 前年同月比")
ax.barh(y + 0.2, per.yoy_vs_target * 100, 0.38, color=LIGHT, label="前年同月比 と 目標比")
ax.set_yticks(y, [f"{k}（季節{s:.0%}）" for k, s in zip(per.kpi, per.season_share)]); ax.invert_yaxis()
ax.set_xlabel("「良い／悪い」が食い違った月の割合（%、2024〜2025年の24か月）"); ax.legend(frameon=False, loc="lower right")
ax.set_title("季節の強い KPI ほど、前月比の矢印は前年同月比と食い違う")
save(fig, "a278_disagree_by_kpi.png")

# 図3：季節の強さと食い違い
fig, ax = plt.subplots(figsize=(6.8, 4.3))
ax.scatter(per.season_share * 100, per.mom_vs_yoy * 100, s=50, color=BLUE)
for _, r in per.iterrows(): ax.annotate(r.kpi, (r.season_share * 100, r.mom_vs_yoy * 100), xytext=(4, 3), textcoords="offset points", fontsize=8.5)
ax.axhline(100 / 3, color=GRAY, lw=0.8, ls="--"); ax.text(1, 34.5, "季節も伸びもなく毎月ばらばらに揺れるだけなら約33%", fontsize=8, color=GRAY)
ax.set_xlabel("季節の強さ（月の違いで説明できる揺れの割合、%）"); ax.set_ylabel("前月比と前年同月比の食い違い（%）")
ax.set_xlim(0, 100); ax.set_ylim(0, 80)
ax.set_title("季節の強さと、前月比の矢印の当てにならなさ")
save(fig, "a278_season_vs_disagree.png")
