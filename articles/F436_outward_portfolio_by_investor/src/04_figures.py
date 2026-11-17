"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
R, F = ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：財務省「対外及び対内証券売買契約等の状況」をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
a = pd.read_csv(R / "annual_net.csv")
net = a.pivot_table(index=["asset", "year"], columns="sector", values="net") / 1e4
GROUP = {"投資信託委託会社等": ["investment_trusts"], "信託勘定": ["trust_accounts"], "銀行等（銀行勘定）": ["banks"],
         "生命保険会社": ["life_insurers"], "金融商品取引業者": ["securities_firms"],
         "そのほか": ["central_bank", "general_gov", "trust_banks_own", "nonlife_insurers", "others"]}
GC = [C[1], C[0], C[2], C[3], C[4], C[5]]


def stacked(ax, t):
    yrs = t.index.values
    pos = np.zeros(len(yrs)); neg = np.zeros(len(yrs))
    for (lab, cols), col in zip(GROUP.items(), GC):
        v = t[cols].sum(axis=1).values
        b = np.where(v >= 0, pos, neg)
        ax.bar(yrs, v, bottom=b, color=col, width=0.72, label=lab)
        pos = pos + np.where(v >= 0, v, 0); neg = neg + np.where(v < 0, v, 0)
    ax.plot(yrs, t["all"].values, color=INK, marker="o", ms=4, lw=1.4, label="全部門の合計")
    ax.axhline(0, color=INK2, lw=0.8)
    ax.set_xticks(range(2005, 2026, 2))
    ax.set_ylabel("ネットの取得（兆円、買い越しが正）")
    style(ax)


# 図1 株式の年ごとのネット取得
fig, ax = plt.subplots(figsize=(8.8, 5.2))
stacked(ax, net.loc["equity"].loc[2005:2025])
ax.legend(frameon=False, loc="lower left", fontsize=8.6, ncol=2)
ax.set_title(f"海外の株式：2024〜25年は投資信託が{m['it_equity_2024_2025']:.1f}兆円を買い越し、信託勘定が{-m['trust_acc_equity_2024_2025']:.1f}兆円を売り越した", loc="left", fontsize=11.5)
fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.14)
save(fig, F / "fig1_equity_by_sector.png", SRC, "注：株式・投資ファンド持分。暦年の合計。「投資信託委託会社等」は投資信託の運用会社など、「信託勘定」は信託銀行が預かって運用する資産。")

# 図2 12か月合計の推移
r = pd.read_csv(R / "rolling12.csv").set_index("ym")
x = (r.index // 100) + ((r.index % 100) - 0.5) / 12
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(x, r.investment_trusts, color=C[1], lw=2.2, label="投資信託委託会社等")
ax.plot(x, r.trust_accounts, color=C[0], lw=2.2, label="信託勘定")
ax.plot(x, r["all"], color=INK, lw=1.3, label="全部門の合計")
ax.axhline(0, color=INK2, lw=0.8)
ax.axvline(2024, color=INK2, lw=0.8, ls="--")
ax.text(2024.1, ax.get_ylim()[1] * 0.92, "2024年1月", fontsize=8.5, color=INK2)
ax.set_xticks(range(2010, 2027, 2))
ax.set_ylabel("直近12か月のネットの取得（兆円）")
ax.legend(frameon=False, loc="lower left", fontsize=9)
style(ax)
ly = q["last_ym"]
ax.set_title(f"株式の12か月合計：{ly//100}年{ly%100}月は投資信託 +{q['it_roll_last']:.1f}兆円、信託勘定 −{-q['ta_roll_last']:.1f}兆円", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig2_equity_rolling12.png", SRC, "注：株式・投資ファンド持分。各月までの12か月のネットの取得の合計。")

# 図3 中長期債の年ごとのネット取得
fig, ax = plt.subplots(figsize=(8.8, 5.2))
stacked(ax, net.loc["longbond"].loc[2005:2025])
ax.legend(frameon=False, loc="lower left", fontsize=8.6, ncol=3)
ax.set_title(f"海外の中長期債：2022年は銀行等が−{-m['banks_longbond_2022']:.1f}兆円、2023年は+{m['banks_longbond_2023']:.1f}兆円", loc="left", fontsize=12)
fig.subplots_adjust(left=0.09, right=0.98, top=0.92, bottom=0.14)
save(fig, F / "fig3_longbond_by_sector.png", SRC, "注：中長期債。暦年の合計。")

# 図4 2024〜25年の部門別
s = pd.read_csv(R / "sector_2024_2025.csv").set_index("sector")
LAB = {"banks": "銀行等（銀行勘定）", "trust_banks_own": "信託銀行（銀行勘定）", "trust_accounts": "信託勘定", "securities_firms": "金融商品取引業者",
       "life_insurers": "生命保険会社", "nonlife_insurers": "損害保険会社", "investment_trusts": "投資信託委託会社等", "others": "その他", "all": "全部門の合計"}
keys = list(LAB)[::-1]
y = np.arange(len(keys))
fig, ax = plt.subplots(figsize=(8.8, 5.2))
h = 0.38
ax.barh(y + h / 2, s.loc[keys, "equity"], height=h, color=C[1], label="株式・投資ファンド持分")
ax.barh(y - h / 2, s.loc[keys, "longbond"], height=h, color=C[0], label="中長期債")
ax.set_yticks(y); ax.set_yticklabels([LAB[k] for k in keys])
ax.axvline(0, color=INK2, lw=0.8)
ax.set_xlabel("2024〜2025年のネットの取得の合計（兆円）")
ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
for i, k in enumerate(keys):
    for off, col in ((h / 2, "equity"), (-h / 2, "longbond")):
        v = s.loc[k, col]
        if abs(v) >= 1:
            ax.text(v + (0.4 if v > 0 else -0.4), i + off, f"{v:+.1f}", va="center", ha="left" if v > 0 else "right", fontsize=8.3, color=INK2)
ax.set_xlim(-26, 24)
ax.legend(frameon=False, loc="upper left", fontsize=9)
ax.set_title(f"2024〜25年：全部門の株式は−{-m['all_equity_2024_2025']:.1f}兆円、中長期債は+{m['all_longbond_2024_2025']:.1f}兆円", loc="left", fontsize=12)
fig.subplots_adjust(left=0.21, right=0.97, top=0.91, bottom=0.15)
save(fig, F / "fig4_sector_2024_2025.png", SRC, "注：中央銀行・一般政府はほぼゼロのため省いた。")
