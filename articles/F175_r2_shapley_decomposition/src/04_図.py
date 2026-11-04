"""04 図：results/ から5枚"""
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GREEN, PURPLE, GRAY, INK

M = [("学び直し_割合", "学び直し（refit）", BLUE), ("SAGE_割合", "周辺でならす（SAGE）", ORANGE),
     ("線形LMG_割合", "線形回帰で学び直し（LMG）", GREEN), ("SHAP取り分", "|SHAP| の取り分（F91 の見方）", PURPLE)]


def methods_fig(name, fname, title):
    t = pd.read_csv(RES / f"shapley_{name}.csv")
    t = t.iloc[::-1].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(8.6, 0.85 * len(t) + 1.4))
    h = 0.2
    for j, (c, lab, col) in enumerate(M):
        y = np.arange(len(t)) + (1.5 - j) * h
        ax.barh(y, t[c] * 100, height=h, color=col, label=lab)
        for yy, v in zip(y, t[c] * 100):
            ax.text(max(v, 0) + 0.6, yy, f"{v:.0f}", va="center", fontsize=7.5, color=INK)
    tot = t["学び直し"].sum()
    lo, hi = t["学び直し_下"] / tot * 100, t["学び直し_上"] / tot * 100
    ax.errorbar(t["学び直し_割合"] * 100, np.arange(len(t)) + 1.5 * h, xerr=[t["学び直し_割合"] * 100 - lo, hi - t["学び直し_割合"] * 100],
                fmt="none", ecolor=INK, lw=0.8, capsize=2)
    ax.set_yticks(np.arange(len(t)), t["グループ"])
    ax.axvline(0, color=GRAY, lw=0.8)
    ax.set_xlabel("R² のうちの取り分（%）　※ |SHAP| は予測の振れ幅の取り分")
    ax.set_title(title, loc="left")
    ax.legend(loc="lower right", fontsize=8.5, frameon=False)
    save(fig, fname)


methods_fig("地価", "f175_land_methods.png", "地価：同じ R² 0.96 を、4つのやり方で7グループに分ける")
methods_fig("電力需要", "f175_power_methods.png", "電力需要：同じ R² 0.98 を、4つのやり方で7グループに分ける")

# 3. 1つだけ外す・Shapley・1つだけ使う
fig, axes = plt.subplots(1, 2, figsize=(11, 5.0))
for ax, name in zip(axes, ["地価", "電力需要"]):
    t = pd.read_csv(RES / f"shapley_{name}.csv")
    vals = [t["1つだけ外す"].sum(), t["学び直し"].sum(), t["1つだけ使う"].sum()]
    labs = ["1つだけ外した\nときの落ち幅\nの合計", "Shapley 値\nの合計\n（＝全変数の R²）", "1つだけ使った\nときの R²\nの合計"]
    b = ax.bar(labs, vals, color=[GRAY, BLUE, ORANGE], width=0.6)
    for bb, v in zip(b, vals):
        ax.text(bb.get_x() + bb.get_width() / 2, v + 0.05, f"{v:.2f}", ha="center", fontsize=10)
    ax.set_title(f"{name}（{len(t)}グループ）", loc="left")
    ax.set_ylim(0, max(vals) * 1.15)
    ax.set_ylabel("R²")
fig.suptitle("「外す」と「使う」は合計が R² に合わない。Shapley 値はその間で、合計がちょうど R² になる", x=0.02, ha="left", fontsize=12.5)
save(fig, "f175_drop_alone.png")

# 4. まとめ方を変える：細かいグループの合計 vs まとめたグループ
rows = []
for name, cname in (("地価", "4グループ"), ("電力需要", "6グループ"), ("電力需要", "4グループ")):
    r = pd.read_csv(RES / f"regroup_{name}_{cname}.csv")
    r["データ"] = name
    rows.append(r)
r = pd.concat(rows)
pick = [("地価", "4グループ", "位置と市区町村"), ("地価", "4グループ", "駅と乗降客数"), ("電力需要", "6グループ", "過去の需要"),
        ("電力需要", "4グループ", "時刻と暦"), ("電力需要", "4グループ", "季節と年")]
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), sharey=True)
for ax, meth, col in zip(axes, ["学び直し", "SAGE"], [BLUE, ORANGE]):
    labs, a, b = [], [], []
    for d, c, g in pick:
        x = r[(r.データ == d) & (r.まとめ方 == c) & (r.方法 == meth) & (r.グループ == g)].iloc[0]
        labs.append(f"{d}：{g}"); a.append(x["細かいグループの合計"]); b.append(x["shapley"])
    y = np.arange(len(labs))[::-1]
    ax.barh(y + 0.18, a, height=0.36, color=GRAY, label="分けて測った値の合計")
    ax.barh(y - 0.18, b, height=0.36, color=col, label="1つにまとめて測った値")
    for yy, v in zip(y + 0.18, a):
        ax.text(v + 0.005, yy, f"{v:.3f}", va="center", fontsize=8)
    for yy, v in zip(y - 0.18, b):
        ax.text(v + 0.005, yy, f"{v:.3f}", va="center", fontsize=8)
    ax.set_yticks(y, labs)
    ax.set_title("学び直し（refit）" if meth == "学び直し" else "周辺でならす（SAGE）", loc="left")
    ax.set_xlabel("Shapley 値（R²）")
    ax.legend(fontsize=8.5, frameon=False, loc="lower right")
fig.suptitle("代わりのきくグループを分けると、学び直しでは取り分の合計がふくらむ", x=0.02, ha="left", fontsize=12.5)
save(fig, "f175_regroup.png")

# 5. 頑健性：見出しのグループの取り分
d = pd.read_csv(RES / "robustness.csv")
fig, axes = plt.subplots(2, 1, figsize=(9.5, 8.8))
for ax, (data, g) in zip(axes, [("地価", "周りの乗降客数"), ("電力需要", "過去の需要")]):
    x = d[(d.データ == data) & (d.グループ == g)].copy()
    x["ラベル"] = x["確かめ方"] + "（" + x["方法"].map({"学び直し": "学び直し", "SAGE": "SAGE"}) + "）"
    x = x.sort_values(["方法", "確かめ方"])
    cols = [BLUE if m == "学び直し" else ORANGE for m in x["方法"]]
    y = np.arange(len(x))[::-1]
    ax.barh(y, x["割合"] * 100, color=cols)
    for yy, v in zip(y, x["割合"] * 100):
        ax.text(v + 0.8, yy, f"{v:.0f}%", va="center", fontsize=8)
    ax.set_yticks(y, x["ラベル"], fontsize=8.5)
    ax.set_xlim(0, 85)
    ax.set_title(f"{data}：「{g}」の取り分", loc="left")
    ax.set_xlabel("R² のうちの取り分（%）")
fig.suptitle("条件を変えても、学び直し（青）と SAGE（橙）の差は残る", x=0.02, ha="left", fontsize=12.5)
fig.tight_layout()
save(fig, "f175_robust.png")
print("ok")
