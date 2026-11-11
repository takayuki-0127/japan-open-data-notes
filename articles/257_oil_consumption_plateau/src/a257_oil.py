"""257 油の消費は、いつから横ばいになったのか

農林水産省「食料需給表」（令和6年度、1960〜2024年度。2024年度は概算値）の油脂類の
  ・国民1人・1年当たり供給純食料（kg、data/jukyu_r6_14.csv）
  ・国民1人・1日当たり供給熱量（kcal、data/jukyu_r6_16.csv）
で、
  1. 折れ線回帰（折れ目1つ、1960〜2021年度）で「伸びが止まった年」を探す
  2. 植物油脂の中身（菜種油・大豆油・その他）と動物油脂の内訳
  3. 1日の供給熱量に占める油脂類の割合
を見る。2022年度以降の減りは折れ線の外で別に見る。
"""
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font

setup_font()


def load(name):
    d = pd.read_csv(DATA / name, header=None)
    yrs = [int(re.match(r"(\d{4})", str(x)).group(1)) for x in d.iloc[11, 2:]]
    return pd.DataFrame({str(d.iloc[i, 1]): pd.to_numeric(pd.Series(d.iloc[i, 2:].values, index=yrs), errors="coerce")
                         for i in range(12, len(d))})


K = load("jukyu_r6_14.csv")
C = load("jukyu_r6_16.csv")
oil = K["油脂類"]
parts = pd.DataFrame({"菜種油": K["油脂類_植物油脂_菜種油"], "大豆油": K["油脂類_植物油脂_大豆油"],
                      "やし油": K["油脂類_植物油脂_やし油"], "その他の植物油": K["油脂類_植物油脂_その他"],
                      "動物油脂": K["油脂類_動物油脂"]})
share = (C["油脂類"] / C["合計"] * 100)


def broken_fit(s, lo, hi, min_seg=5):
    """折れ目1つの連続な折れ線（ヒンジ）を最小二乗で当てはめ、折れ目の年を総当たりで選ぶ"""
    s = s.loc[lo:hi].dropna()
    x = s.index.values.astype(float); y = s.values
    best = None
    for b in range(lo + min_seg, hi - min_seg + 1):
        X = np.column_stack([np.ones_like(x), x - b, np.maximum(x - b, 0)])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        sse = float(((y - X @ coef) ** 2).sum())
        if best is None or sse < best[1]:
            best = (b, sse, coef)
    b, sse, coef = best
    return {"折れ目の年": int(b), "前の傾き（/年）": round(float(coef[1]), 3),
            "後の傾き（/年）": round(float(coef[1] + coef[2]), 3), "残差平方和": round(sse, 2)}, best


fit_kg, best_kg = broken_fit(oil, 1960, 2021)
fit_kc, _ = broken_fit(C["油脂類"], 1960, 2021)
fit_ma, _ = broken_fit(oil.rolling(3, center=True).mean(), 1961, 2021)
fit_kg24, _ = broken_fit(oil, 1960, 2024)
fit_sh, _ = broken_fit(share, 1960, 2021)

res = {
    "油脂類_kg": {int(y): float(oil[y]) for y in [1960, 1970, 1980, 1985, 1990, 2000, 2010, 2019, 2020, 2021, 2022, 2023, 2024]},
    "油脂類_最大": {"年度": int(oil.idxmax()), "kg": float(oil.max())},
    "1985〜2021年度の範囲_kg": [float(oil.loc[1985:2021].min()), float(oil.loc[1985:2021].max())],
    "1985〜2021年度の平均_kg": round(float(oil.loc[1985:2021].mean()), 2),
    "折れ線_重さ_1960〜2021": fit_kg,
    "頑健性_折れ線_熱量_1960〜2021": fit_kc,
    "頑健性_折れ線_3年移動平均": fit_ma,
    "頑健性_折れ線_2024年度まで": fit_kg24,
    "折れ線_熱量の割合_1960〜2021": fit_sh,
    "熱量に占める割合_%": {int(y): round(float(share[y]), 1) for y in [1960, 1980, 1985, 2000, 2021, 2024]},
    "合計の熱量_kcal": {int(y): float(C.loc[y, "合計"]) for y in [1960, 1985, 1996, 2021, 2024]},
    "内訳_kg": {int(y): parts.loc[y].round(1).to_dict() for y in [1960, 1985, 2000, 2021, 2024]},
    "2021→2024_kg": round(float(oil[2024] - oil[2021]), 1),
    "2021→2024_%": round(float((oil[2024] / oil[2021] - 1) * 100), 1),
}
json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"油脂類_kg": oil, "熱量_kcal": C["油脂類"], "熱量の割合_%": share.round(2)}).join(parts).to_csv(RES / "a257_series.csv")

# 図1：油脂類（kg）と折れ線
b, _, coef = best_kg
x = np.arange(1960, 2022)
fitted = coef[0] + coef[1] * (x - b) + coef[2] * np.maximum(x - b, 0)
fig, ax = plt.subplots(figsize=(8.2, 4.3))
ax.plot(oil.index, oil.values, color="#b7791f", lw=2, marker="o", ms=2.5, label="油脂類（1人・1年当たり供給純食料）")
ax.plot(x, fitted, color="#555", lw=1.2, ls="--", label=f"折れ線（折れ目 {b}年度）")
ax.axvspan(2021.5, 2024.5, color="#fed7d7", alpha=0.6)
ax.text(2016.5, 4.5, "2022年度から\n下がった", fontsize=8.5, color="#c53030")
ax.annotate(f"最大 {res['油脂類_最大']['年度']}年度 {res['油脂類_最大']['kg']}kg", (res["油脂類_最大"]["年度"], res["油脂類_最大"]["kg"]),
            xytext=(1993, 17), fontsize=8.5, arrowprops=dict(arrowstyle="->", color="#555"))
ax.set_ylim(0, 18)
ax.set_ylabel("kg／人・年")
ax.set_title(f"油の量は{b}年度ごろに伸びが止まり、2021年度まで13〜15kgで横ばい", fontsize=11)
ax.legend(frameon=False, loc="lower right", fontsize=8.5)
ax.text(0, -0.13, "2024年度は概算値。出典：農林水産省「食料需給表」", transform=ax.transAxes, fontsize=7.5, color="#555")
fig.tight_layout(); fig.savefig(FIG / "a257_oil_kg.png", dpi=150); plt.close(fig)

# 図2：内訳（積み上げ）
fig, ax = plt.subplots(figsize=(8.2, 4.3))
cols = ["#f6e05e", "#d69e2e", "#e2e8f0", "#b7791f", "#718096"]
ax.stackplot(parts.index, *[parts[c] for c in parts], labels=parts.columns, colors=cols)
ax.set_ylabel("kg／人・年")
ax.set_title("植物油が増え、動物油脂は1985年度の2.5kgから0.4kgに減った", fontsize=11)
ax.legend(frameon=False, loc="upper left", fontsize=8.5, ncol=3)
ax.set_ylim(0, 18)
fig.tight_layout(); fig.savefig(FIG / "a257_parts.png", dpi=150); plt.close(fig)

# 図3：熱量に占める割合
fig, ax = plt.subplots(figsize=(8.2, 4.0))
ax.plot(share.index, share.values, color="#b7791f", lw=2)
ax.set_ylabel("1日の供給熱量に占める油脂類（%）")
ax.set_title(f"熱量に占める油の割合：{share[1960]:.1f}%（1960年度）→ {share[2021]:.1f}%（2021年度）→ {share[2024]:.1f}%（2024年度）", fontsize=10.5)
ax.set_ylim(0, 16)
fig.tight_layout(); fig.savefig(FIG / "a257_share.png", dpi=150); plt.close(fig)
print(json.dumps(res, ensure_ascii=False, indent=1))
