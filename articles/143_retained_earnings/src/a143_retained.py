"""内部留保（利益剰余金）は現預金として積み上がっていたのか"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import load_panel, FIG, RES, C

p = load_panel()
w = p.pivot_table(index="fiscal_year", columns=["size", "item"], values="value_million_yen")
T = 1e6  # 百万円 → 兆円

# 規模別の合計が総額と一致するかの確認
chk = (w["small"] + w["medium"] + w["large"] - w["total"]).abs().max().max()
print("size-sum check (百万円):", chk)

t = w["total"] / T
items = ["retained", "cash", "inv_securities", "securities_current", "tangible", "total_assets", "equity"]
t[items].round(2).to_csv(os.path.join(RES, "a143_total_trillion.csv"))

# 1) 推移
fig, ax = plt.subplots(figsize=(8, 4.6))
for k, lab, c in [("retained", "利益剰余金（内部留保）", C[1]), ("tangible", "有形固定資産", C[5]),
                  ("inv_securities", "投資有価証券", C[4]), ("cash", "現金・預金", C[0])]:
    ax.plot(t.index, t[k], marker="o", ms=3, color=c, lw=2, label=lab)
    ax.annotate(f"{t[k].iloc[-1]:.0f}", (t.index[-1], t[k].iloc[-1]), xytext=(4, 0),
                textcoords="offset points", va="center", color=c, fontsize=9)
ax.set_title("利益剰余金と主な資産の推移（全産業・金融保険業を除く）")
ax.set_ylabel("兆円")
ax.set_xlabel("年度")
ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_ylim(0, None)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "a143_trend.png"))

# 2) 2006→2022 の増加分の内訳
y0, y1 = t.index.min(), t.index.max()
d = (t.loc[y1] - t.loc[y0])
other = d["total_assets"] - d[["cash", "securities_current", "inv_securities", "tangible"]].sum()
dec = pd.Series({"現金・預金": d["cash"], "投資有価証券": d["inv_securities"],
                 "有形固定資産": d["tangible"], "有価証券（流動）": d["securities_current"],
                 "その他の資産": other})
dec.round(1).to_csv(os.path.join(RES, "a143_asset_increase.csv"), header=["increase_trillion"])
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.barh(dec.index[::-1], dec.values[::-1], color=[C[5], C[5], C[5], C[4], C[0]])
for i, v in enumerate(dec.values[::-1]):
    ax.text(v + (2 if v >= 0 else -2), i, f"{v:+.0f}", va="center", ha="left" if v >= 0 else "right", fontsize=9)
ax.axvline(0, color="#333", lw=0.8)
ax.set_title(f"{y0}→{y1}年度の資産の増加（計{d['total_assets']:+.0f}兆円）\n同じ期間の利益剰余金の増加は{d['retained']:+.0f}兆円")
ax.set_xlabel("兆円")
fig.tight_layout()
fig.savefig(os.path.join(FIG, "a143_increase.png"))

# 3) 規模別：総資産に占める割合
rows = []
for s, lab in [("small", "資本金1億円未満"), ("medium", "1億〜10億円未満"), ("large", "10億円以上")]:
    g = w[s]
    for y in g.index:
        rows.append({"size": lab, "fiscal_year": y,
                     "cash_ratio": g.loc[y, "cash"] / g.loc[y, "total_assets"] * 100,
                     "retained_ratio": g.loc[y, "retained"] / g.loc[y, "total_assets"] * 100,
                     "invsec_ratio": g.loc[y, "inv_securities"] / g.loc[y, "total_assets"] * 100,
                     "tangible_ratio": g.loc[y, "tangible"] / g.loc[y, "total_assets"] * 100,
                     "cash_trillion": g.loc[y, "cash"] / T, "retained_trillion": g.loc[y, "retained"] / T})
sz = pd.DataFrame(rows)
sz.round(2).to_csv(os.path.join(RES, "a143_by_size.csv"), index=False)
fig, axes = plt.subplots(1, 2, figsize=(9.5, 4.2), sharey=True)
for ax, col, ttl in [(axes[0], "cash_ratio", "現金・預金"), (axes[1], "retained_ratio", "利益剰余金")]:
    for i, (lab, g) in enumerate(sz.groupby("size", sort=False)):
        ax.plot(g["fiscal_year"], g[col], marker="o", ms=3, color=C[i], lw=2, label=lab)
    ax.set_title(f"{ttl}（総資産に占める割合）")
    ax.set_xlabel("年度")
axes[0].set_ylabel("%")
axes[0].legend(frameon=False, fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(FIG, "a143_size.png"))

# 主な数字
s = {}
for k in items:
    s[f"{k}_{y0}"] = t.loc[y0, k]
    s[f"{k}_{y1}"] = t.loc[y1, k]
s["cash_to_retained_inc_ratio"] = d["cash"] / d["retained"]
s["cash_share_assets_y0"] = t.loc[y0, "cash"] / t.loc[y0, "total_assets"] * 100
s["cash_share_assets_y1"] = t.loc[y1, "cash"] / t.loc[y1, "total_assets"] * 100
s["retained_share_assets_y0"] = t.loc[y0, "retained"] / t.loc[y0, "total_assets"] * 100
s["retained_share_assets_y1"] = t.loc[y1, "retained"] / t.loc[y1, "total_assets"] * 100
s["cash_over_retained_y0"] = t.loc[y0, "cash"] / t.loc[y0, "retained"] * 100
s["cash_over_retained_y1"] = t.loc[y1, "cash"] / t.loc[y1, "retained"] * 100
pd.Series(s).round(3).to_csv(os.path.join(RES, "a143_summary.csv"), header=["value"])
print(pd.Series(s).round(2).to_string())
print(dec.round(1).to_string())
print(sz[sz.fiscal_year.isin([y0, 2012, 2019, y1])].round(1).to_string())
