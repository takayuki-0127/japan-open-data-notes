"""227 コーヒーにかけるお金は、家で淹れる分・缶やペットボトル・喫茶店のどこへ移ったのか

家計調査（二人以上の世帯）の3品目
  コーヒー（家庭で淹れる豆・粉・インスタント）／コーヒー飲料（缶・ペットボトルなど）／喫茶代（外食）
の1世帯当たり年間支出を、2015〜2025年で並べ、
  1. 3品目の割合の移り変わり
  2. 家庭のコーヒーの「量（g）×1gあたりの値段」への分解（2019〜2025年、年報の購入数量）
  3. 物価（CPI の対応品目）で割った実質の支出
  4. 喫茶代の世帯主の年齢別の伸び（2019→2025年）
  5. 2026年1〜9月と2025年1〜9月の比較
を出す。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG, AGES, setup_font, annual, monthly, detail, cpi

setup_font()
ITEMS = ["コーヒー", "コーヒー飲料", "喫茶代"]
LAB = {"コーヒー": "家で淹れる（豆・粉・インスタント）", "コーヒー飲料": "缶・ペットボトルなど", "喫茶代": "喫茶代（外食）"}
COL = {"コーヒー": "#7a4b2a", "コーヒー飲料": "#c08a3e", "喫茶代": "#3b6ea5"}

P = annual()[ITEMS]
C = cpi()
share = P.div(P.sum(axis=1), axis=0) * 100

# 物価：家庭用は CPI「インスタントコーヒー」「コーヒー豆」の平均、飲料は「コーヒー飲料Ａ・Ｂ」の平均、
# 喫茶代は「コーヒー（外食）Ａ・Ｂ」の平均（いずれも2020年＝100）
PRICE = {
    "コーヒー": C[["インスタントコーヒー", "コーヒー豆"]].mean(axis=1),
    "コーヒー飲料": C[["コーヒー飲料Ａ", "コーヒー飲料Ｂ"]].mean(axis=1),
    "喫茶代": C[["コーヒー（外食）Ａ", "コーヒー（外食）Ｂ"]].mean(axis=1),
}
real = pd.DataFrame({k: P[k] / PRICE[k] * 100 for k in ITEMS})
real_idx = real / real.loc[2015] * 100
nom_idx = P / P.loc[2015] * 100

# 家庭のコーヒー：年報（第4-6表の「平均」）の購入数量（g）と支出
D = detail()
avg = D[(D.kind == "age") & (D.group == "平均")]
q = avg[(avg.item == "コーヒー") & (avg.metric == "購入数量")].set_index("year").value
s = avg[(avg.item == "コーヒー") & (avg.metric == "支出金額")].set_index("year").value
home = pd.DataFrame({"spend": s, "grams": q})
home["yen_per_100g"] = home.spend / home.grams * 100
hidx = home / home.loc[2019] * 100

# 年齢別の喫茶代（2019→2025年）と1人あたり
ag = D[(D.kind == "age") & D.group.isin(AGES + ["平均"]) & (D.metric == "支出金額")]
cafe = ag[ag.item == "喫茶代"].pivot_table(index="group", columns="year", values="value").loc[AGES + ["平均"]]
hh = ag[ag.item == "世帯人員"].pivot_table(index="group", columns="year", values="value").loc[AGES + ["平均"]]
cafe_pp = cafe / hh
cafe_chg = pd.DataFrame({
    "2019": cafe[2019], "2025": cafe[2025],
    "名目の伸び(%)": (cafe[2025] / cafe[2019] - 1) * 100,
    "実質の伸び(%)": ((cafe[2025] / PRICE["喫茶代"][2025]) / (cafe[2019] / PRICE["喫茶代"][2019]) - 1) * 100,
    "1人あたりの名目の伸び(%)": (cafe_pp[2025] / cafe_pp[2019] - 1) * 100,
})
home_age = ag[ag.item == "コーヒー"].pivot_table(index="group", columns="year", values="value").loc[AGES + ["平均"]]
mix_age = (cafe[2025] / (cafe[2025] + home_age[2025])) * 100

# 2026年1〜9月と2025年1〜9月
m = monthly()
m = m[m.item.isin(ITEMS) & (m.month <= 9)]
ytd = m.groupby(["item", "year"]).value.sum().unstack("year")
ytd_chg = (ytd[2026] / ytd[2025] - 1) * 100

# 結果の保存
P.to_csv(RES / "spend_nominal.csv")
share.round(2).to_csv(RES / "share.csv")
real_idx.round(2).to_csv(RES / "real_index_2015_100.csv")
home.round(3).to_csv(RES / "home_coffee_grams_price.csv")
cafe_chg.round(2).to_csv(RES / "cafe_by_age_2019_2025.csv")
out = {
    "nominal_2015": P.loc[2015].to_dict(), "nominal_2025": P.loc[2025].to_dict(),
    "total_2015": float(P.loc[2015].sum()), "total_2025": float(P.loc[2025].sum()),
    "total_ratio_2025_2015": float(P.loc[2025].sum() / P.loc[2015].sum()),
    "share_2015": share.loc[2015].round(1).to_dict(), "share_2019": share.loc[2019].round(1).to_dict(),
    "share_2020": share.loc[2020].round(1).to_dict(), "share_2025": share.loc[2025].round(1).to_dict(),
    "nominal_idx_2025": nom_idx.loc[2025].round(1).to_dict(),
    "real_idx_2025": real_idx.loc[2025].round(1).to_dict(), "real_idx_2019": real_idx.loc[2019].round(1).to_dict(),
    "home_2019_2025": hidx.loc[2025].round(1).to_dict(),
    "home_grams": home.grams.to_dict(), "home_yen_per_100g": home.yen_per_100g.round(1).to_dict(),
    "cafe_age": cafe_chg.round(1).to_dict(orient="index"),
    "cafe_share_of_cafe_plus_home_2025_by_age": mix_age.round(1).to_dict(),
    "ytd_2026_vs_2025_pct": ytd_chg.round(1).to_dict(),
}
json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False, indent=1))

# 図1：3品目の支出（名目）
fig, ax = plt.subplots(figsize=(8, 4.6))
for k in ITEMS:
    ax.plot(P.index, P[k], marker="o", color=COL[k], label=LAB[k], lw=2)
ax.set_title("コーヒーへの支出（二人以上の世帯、1世帯当たり年間、円）")
ax.set_xticks(P.index)
ax.set_xticklabels([str(y) for y in P.index], fontsize=9)
ax.legend(frameon=False)
ax.grid(axis="y", alpha=.3)
ax.annotate("2020年：喫茶代が減り\n家で淹れる分が増えた", xy=(2020, P.loc[2020, "喫茶代"]), xytext=(2016.6, 8700),
            arrowprops=dict(arrowstyle="->", color="gray"), fontsize=9, color="dimgray")
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」をもとに作成者が加工して作成。2025年は月の表の12か月の合計", fontsize=8, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a227_spend.png", dpi=150)
plt.close(fig)

# 図2：家で淹れるコーヒーの量と値段（2019年＝100）
fig, ax = plt.subplots(figsize=(8, 4.6))
ax.plot(hidx.index, hidx.spend, marker="o", color="#7a4b2a", lw=2, label="支出")
ax.plot(hidx.index, hidx.grams, marker="s", color="#999999", lw=2, label="買った量（g）")
ax.plot(hidx.index, hidx.yen_per_100g, marker="^", color="#c0392b", lw=2, label="100gあたりの値段")
ax.axhline(100, color="gray", lw=.8)
for c, v in [("spend", hidx.spend), ("grams", hidx.grams), ("yen_per_100g", hidx.yen_per_100g)]:
    ax.text(2025.1, v.loc[2025], f"{v.loc[2025]:.0f}", va="center", fontsize=9)
ax.set_title("家で淹れるコーヒー：支出・量・100gあたりの値段（2019年＝100）")
ax.set_xticks(hidx.index)
ax.legend(frameon=False, loc="upper left")
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」年報 第4-6表（平均）をもとに作成者が加工して作成", fontsize=8, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a227_home.png", dpi=150)
plt.close(fig)

# 図3：喫茶代の伸び（2019→2025年、世帯主の年齢別）
fig, ax = plt.subplots(figsize=(8, 4.6))
x = np.arange(len(AGES) + 1)
labs = AGES + ["平均"]
ax.bar(x - 0.2, cafe_chg.loc[labs, "名目の伸び(%)"], 0.4, color="#3b6ea5", label="名目")
ax.bar(x + 0.2, cafe_chg.loc[labs, "実質の伸び(%)"], 0.4, color="#9fbfdf", label="実質（喫茶店のコーヒーの物価で割った）")
for i, l in enumerate(labs):
    ax.text(i - 0.2, cafe_chg.loc[l, "名目の伸び(%)"] + 1.5, f"{cafe_chg.loc[l, '名目の伸び(%)']:.0f}", ha="center", fontsize=8)
    ax.text(i + 0.2, cafe_chg.loc[l, "実質の伸び(%)"] + 1.5, f"{cafe_chg.loc[l, '実質の伸び(%)']:.0f}", ha="center", fontsize=8)
ax.set_xticks(x)
ax.set_xticklabels(labs)
ax.set_ylabel("2019→2025年の伸び（%）")
ax.set_title("喫茶代の伸び（2019→2025年、世帯主の年齢別）")
ax.legend(frameon=False)
ax.grid(axis="y", alpha=.3)
fig.text(0.01, 0.01, "出典：総務省統計局「家計調査」年報 第4-6表、「消費者物価指数」をもとに作成者が加工して作成。29歳以下は集計世帯が約100と少ない", fontsize=7.5, color="gray")
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "a227_cafe_age.png", dpi=150)
plt.close(fig)
