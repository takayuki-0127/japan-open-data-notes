"""228 外食は、どの年齢の世帯で減り、どこで戻ったのか

家計調査 年報 第4-6表（世帯主の年齢階級別、二人以上の世帯）の「一般外食」（学校給食を除く外食）と、
その内訳の食事代・喫茶代・飲酒代を、2019〜2025年で比べる。
  1. 年齢別の一般外食（2019年＝100）の名目と、CPI「一般外食」で割った実質
  2. 全体（平均）の戻りが各年齢より小さく見える理由：世帯の年齢構成の変化（2019年の構成に固定した平均と比べる）
  3. 内訳（食事代・喫茶代・飲酒代）の実質の戻り（2025年／2019年）
  4. 全国の長期（2015〜2025年）と、2026年1〜9月の前年同期比
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, AGES, setup_font, annual, monthly, detail, cpi

setup_font()
C = cpi()
D = detail()
x = D[(D.kind == "age") & (D.metric == "支出金額")]


def tab(item):
    return x[x.item == item].pivot_table(index="group", columns="year", values="value")


ge = tab("一般外食")
w = tab("世帯数分布(抽出率調整)").loc[AGES]          # 1万世帯あたりの世帯数（抽出率調整）
n = tab("集計世帯数").loc[AGES + ["平均"]]
hh = tab("世帯人員").loc[AGES + ["平均"]]
YEARS = list(ge.columns)

# 1. 年齢別の指数（2019年＝100）
nom = ge.loc[AGES + ["平均"]]
nom_idx = nom.div(nom[2019], axis=0) * 100
real = nom / C.loc[YEARS, "一般外食"].values * 100
real_idx = real.div(real[2019], axis=0) * 100

# 2. 年齢構成の効果：各年齢の値を、その年の構成（公表の平均）と2019年の構成で平均する
w_share = w / w.sum()
fixed = (nom.loc[AGES].mul(w_share[2019], axis=0)).sum()
actual_w = (nom.loc[AGES] * w_share).sum()
mix = pd.DataFrame({"公表の平均": nom.loc["平均"], "各年の構成で平均": actual_w, "2019年の構成に固定": fixed})
mix_idx = mix / mix.loc[2019] * 100
mix_gap_2025 = mix_idx.loc[2025, "2019年の構成に固定"] - mix_idx.loc[2025, "各年の構成で平均"]

# 3. 内訳の実質の戻り（2025年／2019年）。喫茶代は CPI「コーヒー（外食）」、飲酒代は「ビール（外食）」で割った場合も出す
sub = {}
for it in ["食事代", "喫茶代", "飲酒代"]:
    t = tab(it).loc[AGES + ["平均"]]
    sub[it] = (t[2025] / C.loc[2025, "一般外食"]) / (t[2019] / C.loc[2019, "一般外食"]) * 100
sub = pd.DataFrame(sub)
alt = pd.DataFrame({
    "喫茶代（喫茶の物価で割る）": (tab("喫茶代").loc[AGES + ["平均"], 2025] / C.loc[2025, ["コーヒー（外食）Ａ", "コーヒー（外食）Ｂ"]].mean())
    / (tab("喫茶代").loc[AGES + ["平均"], 2019] / C.loc[2019, ["コーヒー（外食）Ａ", "コーヒー（外食）Ｂ"]].mean()) * 100,
    "飲酒代（ビール（外食）の物価で割る）": (tab("飲酒代").loc[AGES + ["平均"], 2025] / C.loc[2025, "ビール（外食）"])
    / (tab("飲酒代").loc[AGES + ["平均"], 2019] / C.loc[2019, "ビール（外食）"]) * 100,
})

# 1人あたり（世帯人員で割る）の実質の戻り
pp = (real / hh)
pp_idx = pp.div(pp[2019], axis=0) * 100

# 4. 全国の長期と2026年
P = annual()
nat = P[["外食", "一般外食", "学校給食"]]
nat_real = nat["一般外食"] / C["一般外食"] * 100
m = monthly()
m = m[m.item.isin(["一般外食", "食事代", "喫茶代", "飲酒代"]) & (m.month <= 9)]
ytd = m.groupby(["item", "year"]).value.sum().unstack("year")
ytd_chg = (ytd[2026] / ytd[2025] - 1) * 100
cpi26 = None  # 2026年の CPI 年平均はまだないので、2026年は名目だけ

# 保存
nom_idx.round(2).to_csv(RES / "general_eating_out_nominal_2019_100.csv")
real_idx.round(2).to_csv(RES / "general_eating_out_real_2019_100.csv")
mix_idx.round(2).to_csv(RES / "age_mix_effect.csv")
sub.round(1).to_csv(RES / "sub_items_real_2025_vs_2019.csv")
alt.round(1).to_csv(RES / "sub_items_real_alt_deflator.csv")
pd.concat({"世帯数分布": w, "集計世帯数": n.loc[AGES]}, axis=1).to_csv(RES / "households_by_age.csv")
out = {
    "nominal_2025_vs_2019": nom_idx[2025].round(1).to_dict(),
    "nominal_2021_vs_2019": nom_idx[2021].round(1).to_dict(),
    "real_2025_vs_2019": real_idx[2025].round(1).to_dict(),
    "real_per_person_2025_vs_2019": pp_idx[2025].round(1).to_dict(),
    "first_year_back_to_2019_nominal": {a: next((int(y) for y in YEARS if y > 2019 and nom_idx.loc[a, y] >= 100), None) for a in AGES + ["平均"]},
    "mix_idx_2025": mix_idx.loc[2025].round(1).to_dict(),
    "mix_gap_2025_pt": round(float(mix_gap_2025), 1),
    "weight_share_70plus": {int(y): round(float(w_share.loc["70歳以上", y]) * 100, 1) for y in YEARS},
    "sub_real_2025_vs_2019": sub.round(1).to_dict(),
    "sub_real_alt": alt.round(1).to_dict(),
    "cpi_general_eating_out_2025_vs_2019": round(float(C.loc[2025, "一般外食"] / C.loc[2019, "一般外食"] * 100), 1),
    "national_general_eating_out": nat["一般外食"].to_dict(),
    "national_real_2025_vs_2015": round(float(nat_real[2025] / nat_real[2015] * 100), 1),
    "national_real_2025_vs_2019": round(float(nat_real[2025] / nat_real[2019] * 100), 1),
    "ytd_2026_vs_2025_nominal_pct": ytd_chg.round(1).to_dict(),
    "n_households_2025": n[2025].to_dict(),
}
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

COLS = dict(zip(AGES, ["#1b9e77", "#66a61e", "#7570b3", "#e7298a", "#d95f02", "#a6761d"]))

# 図1：年齢別の一般外食（実質、2019年＝100）
fig, ax = plt.subplots(figsize=(8, 4.8))
ys = {a: real_idx.loc[a, 2025] for a in AGES}
order = sorted(AGES, key=lambda a: ys[a])
pos, prev = {}, -1e9
for a in order:                      # 右端のラベルが重ならないように少しずらす
    pos[a] = max(ys[a], prev + 2.6)
    prev = pos[a]
for a in AGES:
    ax.plot(YEARS, real_idx.loc[a], marker="o", lw=1.8, color=COLS[a], label=a)
    ax.text(2025.12, pos[a], f"{a} {ys[a]:.0f}", va="center", fontsize=8, color=COLS[a])
ax.plot(YEARS, real_idx.loc["平均"], marker="s", lw=2.8, color="black", label="平均")
ax.axhline(100, color="gray", lw=.8)
ax.set_xlim(2018.7, 2026.4)
ax.set_xticks(YEARS)
ax.set_title("一般外食（学校給食を除く）の支出、世帯主の年齢別（実質、2019年＝100）")
ax.legend(frameon=False, ncol=4, fontsize=8, loc="lower right")
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」年報 第4-6表（二人以上の世帯）、「消費者物価指数」（一般外食）をもとに作成者が加工して作成", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a228_real_by_age.png", dpi=150)
plt.close(fig)

# 図2：内訳の実質の戻り（2025年／2019年）
fig, ax = plt.subplots(figsize=(8, 4.8))
labs = AGES + ["平均"]
xx = np.arange(len(labs))
for k, (it, c) in enumerate(zip(["食事代", "喫茶代", "飲酒代"], ["#4c72b0", "#dd8452", "#c44e52"])):
    v = sub.loc[labs, it]
    ax.bar(xx + (k - 1) * 0.27, v, 0.27, color=c, label=it)
    for i, val in enumerate(v):
        ax.text(xx[i] + (k - 1) * 0.27, val + 2, f"{val:.0f}", ha="center", fontsize=7)
ax.axhline(100, color="gray", lw=.8)
ax.set_xticks(xx)
ax.set_xticklabels(labs)
ax.set_ylabel("2025年の実質（2019年＝100）")
ax.set_title("外食の内訳の戻り（実質、2025年／2019年、世帯主の年齢別）")
ax.legend(frameon=False, ncol=3)
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」年報 第4-6表、「消費者物価指数」（一般外食）をもとに作成者が加工して作成。29歳以下は集計世帯が約100と少ない", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a228_sub_items.png", dpi=150)
plt.close(fig)

# 図3：年齢構成の効果
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(YEARS, mix_idx["公表の平均"], marker="o", lw=2.4, color="black", label="公表の平均（その年の世帯の年齢構成）")
ax.plot(YEARS, mix_idx["2019年の構成に固定"], marker="s", lw=2, color="#d95f02", ls="--", label="世帯の年齢構成を2019年に固定した平均")
for c in ["公表の平均", "2019年の構成に固定"]:
    ax.text(2025.1, mix_idx.loc[2025, c], f"{mix_idx.loc[2025, c]:.1f}", va="center", fontsize=9)
ax.axhline(100, color="gray", lw=.8)
ax.set_xlim(2018.7, 2025.8)
ax.set_title("一般外食の平均（名目、2019年＝100）：世帯の年齢構成の変化の分")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, f"70歳以上の世帯の割合：{w_share.loc['70歳以上', 2019]*100:.1f}%（2019年）→{w_share.loc['70歳以上', 2025]*100:.1f}%（2025年）。出典：総務省統計局「家計調査」年報 第4-6表をもとに作成者が加工して作成", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a228_age_mix.png", dpi=150)
plt.close(fig)
