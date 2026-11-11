"""229 お菓子の支出は、物価を除くと増えているのか

家計調査（二人以上の世帯）の「菓子類」の1世帯当たり年間支出（2015〜2025年）を、
消費者物価指数（2020年基準）の「菓子類」で割って実質にし、
  1. 名目と実質の推移（2015年＝100）
  2. 品目ごとの 2019→2025年の名目の伸びを「値段の伸び（CPI）」と「それ以外（実質＝おおよその量）」に分ける
  3. 世帯主の年齢別の実質の伸び（2019→2025年、年報 第4-6表）
  4. 2026年1〜9月の名目の前年同期比
を出す。品目と CPI の対応は MAP（対応する CPI 品目がないものは近い品目で代用）。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, AGES, setup_font, annual, monthly, detail, cpi

setup_font()
P = annual()
C = cpi()
YRS = list(range(2015, 2026))

# 家計調査の品目 → CPI の品目（複数は単純平均）。* は近い品目での代用
MAP = {
    "ようかん": ["ようかん"], "まんじゅう": ["まんじゅう"], "他の和生菓子": ["だいふく餅"],  # *
    "カステラ": ["カステラ"], "ケーキ": ["ケーキ", "ロールケーキ"], "ゼリー": ["ゼリー"], "プリン": ["プリン"],
    "他の洋生菓子": ["ケーキ", "ロールケーキ", "プリン", "ゼリー"],  # *
    "せんべい": ["せんべい"], "ビスケット": ["ビスケット"], "スナック菓子": ["ポテトチップス"],  # *
    "キャンデー": ["キャンデー"], "チョコレート": ["チョコレート"], "チョコレート菓子": ["チョコレート"],  # *
    "アイスクリーム・シャーベット": ["アイスクリーム"], "他の菓子": ["菓子類"],  # *
}
PROXY = {"他の和生菓子", "他の洋生菓子", "スナック菓子", "チョコレート菓子", "他の菓子"}

tot = P["菓子類"].loc[YRS]
price = C.loc[YRS, "菓子類"]
real = tot / price * 100
nom_idx = tot / tot[2015] * 100
real_idx = real / real[2015] * 100
price_idx = price / price[2015] * 100
peak_year = int(real_idx.idxmax())

# 品目別：2019→2025年
rows = []
for it, cs in MAP.items():
    pr = C[cs].mean(axis=1)
    n = P.loc[2025, it] / P.loc[2019, it]
    p = pr[2025] / pr[2019]
    rows.append({"品目": it, "2019年（円）": P.loc[2019, it], "2025年（円）": P.loc[2025, it],
                 "名目の伸び(%)": (n - 1) * 100, "値段の伸び(%)": (p - 1) * 100, "実質の伸び(%)": (n / p - 1) * 100,
                 "対応するCPI": "・".join(cs) + ("（代用）" if it in PROXY else "")})
items = pd.DataFrame(rows).set_index("品目").sort_values("実質の伸び(%)")
# 実質の増減への寄与（2019年の支出の割合 × 実質の伸び）
share19 = items["2019年（円）"] / P.loc[2019, "菓子類"]
items["実質の増減への寄与(pt)"] = share19 * items["実質の伸び(%)"]

# 年齢別（年報 第4-6表）
D = detail()
x = D[(D.kind == "age") & (D.metric == "支出金額")]
ag = x[x.item == "菓子類"].pivot_table(index="group", columns="year", values="value").loc[AGES + ["平均"]]
hh = x[x.item == "世帯人員"].pivot_table(index="group", columns="year", values="value").loc[AGES + ["平均"]]
pc = C.loc[2025, "菓子類"] / C.loc[2019, "菓子類"]
age = pd.DataFrame({
    "2019年（円）": ag[2019], "2025年（円）": ag[2025],
    "名目の伸び(%)": (ag[2025] / ag[2019] - 1) * 100,
    "実質の伸び(%)": (ag[2025] / ag[2019] / pc - 1) * 100,
    "1人あたり実質の伸び(%)": ((ag[2025] / hh[2025]) / (ag[2019] / hh[2019]) / pc - 1) * 100,
})

# 2026年1〜9月
m = monthly()
m = m[(m.item == "菓子類") & (m.month <= 9)]
ytd = m.groupby("year").value.sum()
ytd_chg = (ytd[2026] / ytd[2025] - 1) * 100
share_food = (P["菓子類"] / P["食料"] * 100).loc[YRS]

# 保存
pd.DataFrame({"名目（円）": tot, "CPI菓子類": price, "実質（2020年価格、円）": real,
              "名目指数": nom_idx, "実質指数": real_idx, "物価指数": price_idx}).round(2).to_csv(RES / "sweets_total.csv")
items.round(2).to_csv(RES / "items_2019_2025.csv")
age.round(2).to_csv(RES / "by_age_2019_2025.csv")
out = {
    "nominal_2015": float(tot[2015]), "nominal_2025": float(tot[2025]),
    "nominal_idx_2025": round(float(nom_idx[2025]), 1), "real_idx_2025": round(float(real_idx[2025]), 1),
    "price_idx_2025": round(float(price_idx[2025]), 1),
    "real_idx_by_year": real_idx.round(1).to_dict(), "nominal_idx_by_year": nom_idx.round(1).to_dict(),
    "real_peak_year": peak_year, "real_2025_vs_2022": round(float(real[2025] / real[2022] * 100), 1),
    "real_2025_vs_2019": round(float(real[2025] / real[2019] * 100), 1),
    "price_2025_vs_2019": round(float(price[2025] / price[2019] * 100), 1),
    "items": items[["名目の伸び(%)", "値段の伸び(%)", "実質の伸び(%)", "実質の増減への寄与(pt)"]].round(1).to_dict(orient="index"),
    "age": age.round(1).to_dict(orient="index"),
    "ytd_2026_vs_2025_nominal_pct": round(float(ytd_chg), 1),
    "share_of_food_pct": share_food.round(2).to_dict(),
}
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# 図1：名目・実質・物価
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(YRS, nom_idx, marker="o", lw=2.2, color="#c0392b", label="支出（名目）")
ax.plot(YRS, price_idx, marker="^", lw=1.8, color="#999999", label="お菓子の物価（CPI 菓子類）")
ax.plot(YRS, real_idx, marker="s", lw=2.6, color="#2c6e49", label="支出（実質＝名目÷物価）")
for s, c in [(nom_idx, "#c0392b"), (price_idx, "#777777"), (real_idx, "#2c6e49")]:
    ax.text(2025.15, s[2025], f"{s[2025]:.1f}", va="center", fontsize=9, color=c)
ax.axhline(100, color="gray", lw=.8)
ax.set_xticks(YRS)
ax.set_xlim(2014.6, 2025.9)
ax.set_title("お菓子（菓子類）への支出：名目と実質（2015年＝100）")
ax.legend(frameon=False, loc="upper left")
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」（二人以上の世帯）、「消費者物価指数」をもとに作成者が加工して作成。2025年は月の表の12か月の合計", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a229_total.png", dpi=150)
plt.close(fig)

# 図2：品目別の名目と実質の伸び（2019→2025年）
it = items.sort_values("実質の伸び(%)")
fig, ax = plt.subplots(figsize=(8, 5.4))
yy = np.arange(len(it))
ax.barh(yy + 0.2, it["名目の伸び(%)"], 0.4, color="#e8a39b", label="名目の伸び")
ax.barh(yy - 0.2, it["実質の伸び(%)"], 0.4, color="#2c6e49", label="実質の伸び（名目÷値段）")
ax.set_yticks(yy)
ax.set_yticklabels([f"{i}{'＊' if i in PROXY else ''}" for i in it.index], fontsize=9)
ax.axvline(0, color="gray", lw=.8)
for i, (n, r) in enumerate(zip(it["名目の伸び(%)"], it["実質の伸び(%)"])):
    ax.text(n + (1 if n >= 0 else -1), i + 0.2, f"{n:.0f}", va="center", ha="left" if n >= 0 else "right", fontsize=7.5)
    ax.text(r + (1 if r >= 0 else -1), i - 0.2, f"{r:.0f}", va="center", ha="left" if r >= 0 else "right", fontsize=7.5, color="#2c6e49")
ax.set_xlabel("2019→2025年の伸び（%）")
ax.set_title("お菓子の品目別：名目と実質の伸び（2019→2025年）")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="x", alpha=.3)
fig.text(0.01, 0.01, "＊は対応する物価がないため近い品目で代用。出典：総務省統計局「家計調査」「消費者物価指数」をもとに作成者が加工して作成", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a229_items.png", dpi=150)
plt.close(fig)

# 図3：年齢別の実質の伸び
fig, ax = plt.subplots(figsize=(8, 4.4))
labs = AGES + ["平均"]
xx = np.arange(len(labs))
ax.bar(xx - 0.2, age.loc[labs, "実質の伸び(%)"], 0.4, color="#2c6e49", label="1世帯あたり")
ax.bar(xx + 0.2, age.loc[labs, "1人あたり実質の伸び(%)"], 0.4, color="#9cc5a1", label="1人あたり（世帯人員で割る）")
for i, l in enumerate(labs):
    for off, col in [(-0.2, "実質の伸び(%)"), (0.2, "1人あたり実質の伸び(%)")]:
        v = age.loc[l, col]
        ax.text(i + off, v + (0.6 if v >= 0 else -0.6), f"{v:.0f}", ha="center", va="bottom" if v >= 0 else "top", fontsize=8)
ax.axhline(0, color="gray", lw=.8)
ax.set_ylim(min(age[["実質の伸び(%)", "1人あたり実質の伸び(%)"]].min()) - 3, 2)
ax.set_xticks(xx)
ax.set_xticklabels(labs)
ax.set_ylabel("実質の伸び（%）")
ax.set_title("お菓子の実質の伸び（2019→2025年、世帯主の年齢別）")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」年報 第4-6表、「消費者物価指数」（菓子類）をもとに作成者が加工して作成。29歳以下は集計世帯が約100と少ない", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a229_age.png", dpi=150)
plt.close(fig)
