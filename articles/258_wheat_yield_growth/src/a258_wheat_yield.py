"""258 小麦の10a当たり収量は、どれだけ上がったのか

農林水産省「作物統計調査」の収穫量累年統計（小麦：全国 1878〜2024年、北海道・都府県 1958〜2024年）で、
  1. 全国の10a当たり収量の長期の推移と、10年平均の伸び
  2. 全国の伸びを「北海道と都府県それぞれの収量の伸び」と「北海道の面積の割合が増えた分」に分ける（シフト・シェア分解）
  3. 年ごとの揺れ（LOWESS のトレンドからの偏差）が、収量の伸びとともにどう変わったか
を見る。data/ の CSV は e-Stat の Excel をそのまま CSV にしたもの。
"""
import csv
import json
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.nonparametric.smoothers_lowess import lowess
from common import DATA, RES, FIG, setup_font

setup_font()


def load(name):
    out = []
    for r in csv.reader(open(DATA / name, encoding="utf-8")):
        m = re.search(r"\((\d{4})\)", r[0] or "")
        if not m:
            continue
        f = lambda v: float(v.replace(",", "")) if re.fullmatch(r"[\d.,]+", v.strip() or "x") else np.nan
        out.append((int(m.group(1)), f(r[1]), f(r[2]), f(r[3]), f(r[4])))
    return pd.DataFrame(out, columns=["year", "area_ha", "yield_kg", "harvest_t", "index"]).set_index("year")


Z, H, T = load("wheat_zenkoku.csv"), load("wheat_hokkaido.csv"), load("wheat_tofuken.csv")
D = pd.DataFrame({"全国": Z["yield_kg"], "北海道": H["yield_kg"], "都府県": T["yield_kg"],
                  "北海道の面積の割合": H["area_ha"] / Z["area_ha"], "全国の面積_ha": Z["area_ha"]})
D.to_csv(RES / "a258_series.csv")

# 検算：北海道と都府県の収穫量・面積から全国の10a当たり収量を作り直す
recon = (H["harvest_t"] + T["harvest_t"]) / (H["area_ha"] + T["area_ha"]) * 1000 / 10
chk = (recon - Z["yield_kg"]).dropna()

P0, P1 = (1958, 1967), (2015, 2024)
m0, m1 = D.loc[P0[0]:P0[1]].mean(), D.loc[P1[0]:P1[1]].mean()
# 面積で重みづけした期間平均（期間の合計収穫量 ÷ 合計面積）
def wmean(df, a, b):
    s = df.loc[a:b]
    return float(s["harvest_t"].sum() / s["area_ha"].sum() * 100)
YH0, YH1 = wmean(H, *P0), wmean(H, *P1)
YT0, YT1 = wmean(T, *P0), wmean(T, *P1)
YZ0, YZ1 = wmean(Z, *P0), wmean(Z, *P1)
sH0 = H.loc[P0[0]:P0[1], "area_ha"].sum() / Z.loc[P0[0]:P0[1], "area_ha"].sum()
sH1 = H.loc[P1[0]:P1[1], "area_ha"].sum() / Z.loc[P1[0]:P1[1], "area_ha"].sum()
# シフト・シェア（2時点の平均の重み）
within = ((sH0 + sH1) / 2) * (YH1 - YH0) + ((1 - sH0 + 1 - sH1) / 2) * (YT1 - YT0)
share_eff = (sH1 - sH0) * ((YH0 + YH1) / 2 - (YT0 + YT1) / 2)
tot = (sH1 * YH1 + (1 - sH1) * YT1) - (sH0 * YH0 + (1 - sH0) * YT0)


def decompose(a0, b0, a1, b1):
    def w(df, a, b):
        s = df.loc[a:b]; return s["harvest_t"].sum() / s["area_ha"].sum() * 100
    h0, h1, t0, t1 = w(H, a0, b0), w(H, a1, b1), w(T, a0, b0), w(T, a1, b1)
    s0 = H.loc[a0:b0, "area_ha"].sum() / Z.loc[a0:b0, "area_ha"].sum()
    s1 = H.loc[a1:b1, "area_ha"].sum() / Z.loc[a1:b1, "area_ha"].sum()
    wi = ((s0 + s1) / 2) * (h1 - h0) + ((2 - s0 - s1) / 2) * (t1 - t0)
    sh = (s1 - s0) * ((h0 + h1) / 2 - (t0 + t1) / 2)
    return {"北海道の伸び": round(float(((s0 + s1) / 2) * (h1 - h0)), 1), "都府県の伸び": round(float(((2 - s0 - s1) / 2) * (t1 - t0)), 1),
            "面積の割合の変化": round(float(sh), 1), "合計": round(float(wi + sh), 1)}


# 揺れ：対数収量の LOWESS トレンドからの偏差（%）
def devs(s, frac=0.3):
    s = s.dropna(); ly = np.log(s.values)
    tr = lowess(ly, s.index.values, frac=frac, return_sorted=False)
    return pd.Series((np.exp(ly - tr) - 1) * 100, index=s.index)


dz = devs(Z["yield_kg"].loc[1878:2024]); dh = devs(H["yield_kg"]); dt = devs(T["yield_kg"])
PER = [(1878, 1919), (1920, 1957), (1958, 1989), (1990, 2024)]
res = {
    "全国_10a当たり収量": {int(y): float(Z.loc[y, "yield_kg"]) for y in [1878, 1900, 1940, 1960, 1970, 1990, 2000, 2010, 2015, 2020, 2023, 2024]},
    "全国_10年平均": {f"{a}〜{a+9}年": round(float(Z.loc[a:a + 9, "yield_kg"].mean()), 1) for a in range(1958, 2015, 10)},
    "全国_2015〜2024年平均": round(float(Z.loc[2015:2024, "yield_kg"].mean()), 1),
    "期間平均（面積で重みづけ）": {"1958〜1967_全国": round(YZ0, 1), "2015〜2024_全国": round(YZ1, 1),
                       "1958〜1967_北海道": round(YH0, 1), "2015〜2024_北海道": round(YH1, 1),
                       "1958〜1967_都府県": round(YT0, 1), "2015〜2024_都府県": round(YT1, 1),
                       "北海道の面積の割合_前": round(float(sH0), 3), "北海道の面積の割合_後": round(float(sH1), 3)},
    "分解_1958〜67→2015〜24": decompose(1958, 1967, 2015, 2024),
    "頑健性_分解_1960〜69→2010〜19": decompose(1960, 1969, 2010, 2019),
    "頑健性_分解_1975〜84→2015〜24": decompose(1975, 1984, 2015, 2024),
    "全国の収量_倍率_1958〜67→2015〜24": round(YZ1 / YZ0, 3),
    "検算_北海道＋都府県から作った全国との差_kg_最大絶対値": round(float(chk.abs().max()), 1),
    "検算_差が2kgを超えた年の数": int((chk.abs() > 2).sum()),
    "揺れ_全国_偏差の標準偏差（%）": {f"{a}〜{b}年": round(float(dz.loc[a:b].std()), 1) for a, b in PER},
    "揺れ_北海道_偏差の標準偏差（%）": {"1958〜1989年": round(float(dh.loc[1958:1989].std()), 1), "1990〜2024年": round(float(dh.loc[1990:2024].std()), 1)},
    "揺れ_都府県_偏差の標準偏差（%）": {"1958〜1989年": round(float(dt.loc[1958:1989].std()), 1), "1990〜2024年": round(float(dt.loc[1990:2024].std()), 1)},
    "揺れ_頑健性_frac0.2_全国": {f"{a}〜{b}年": round(float(devs(Z['yield_kg'].loc[1878:2024], 0.2).loc[a:b].std()), 1) for a, b in PER},
    "大きく落ちた年_1990年以降_全国（偏差−10%以下）": {int(y): round(float(v), 1) for y, v in dz.loc[1990:].items() if v <= -10},
    "大きく落ちた年_1990年以降_北海道（偏差−15%以下）": {int(y): round(float(v), 1) for y, v in dh.loc[1990:].items() if v <= -15},
    "大きく落ちた年_1990年以降_都府県（偏差−15%以下）": {int(y): round(float(v), 1) for y, v in dt.loc[1990:].items() if v <= -15},
}
json.dump(res, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"全国": dz.round(2), "北海道": dh.round(2), "都府県": dt.round(2)}).to_csv(RES / "a258_deviation.csv")

# 図1：全国の長期推移
fig, ax = plt.subplots(figsize=(8.4, 4.2))
ax.plot(Z.index, Z["yield_kg"], color="#b7791f", lw=1.6)
ma = Z["yield_kg"].rolling(10, center=True).mean()
ax.plot(ma.index, ma.values, color="#555", lw=1.2, ls="--", label="10年移動平均")
for y in [1903, 1945, 2010]:
    ax.annotate(f"{y}年 {int(Z.loc[y,'yield_kg'])}kg", (y, Z.loc[y, "yield_kg"]), xytext=(y - 12, Z.loc[y, "yield_kg"] - 45), fontsize=8,
                arrowprops=dict(arrowstyle="->", color="#888"))
ax.set_ylabel("10a当たり収量（kg）")
ax.set_title("小麦の10a当たり収量（全国）：71kg（1878年）→ 444kg（2024年）", fontsize=11)
ax.legend(frameon=False, loc="upper left")
ax.text(0, -0.13, "出典：農林水産省「作物統計調査」収穫量累年統計（小麦）", transform=ax.transAxes, fontsize=7.5, color="#555")
fig.tight_layout(); fig.savefig(FIG / "a258_long.png", dpi=150); plt.close(fig)

# 図2：北海道・都府県と北海道の面積割合
fig, ax = plt.subplots(figsize=(8.4, 4.4))
ax.plot(D.index, D["北海道"], color="#2b6cb0", lw=1.6, label="北海道")
ax.plot(D.index, D["都府県"], color="#c05621", lw=1.6, label="都府県")
ax.plot(D.loc[1958:].index, D.loc[1958:, "全国"], color="#555", lw=1.2, ls=":", label="全国")
ax.set_ylabel("10a当たり収量（kg）")
ax2 = ax.twinx()
ax2.fill_between(D.loc[1958:].index, 0, D.loc[1958:, "北海道の面積の割合"] * 100, color="#bee3f8", alpha=0.45, zorder=0)
ax2.set_ylabel("北海道の面積の割合（%、青い面）")
ax2.set_ylim(0, 100)
ax.set_zorder(ax2.get_zorder() + 1); ax.patch.set_visible(False)
ax.set_xlim(1957, 2025)
ax.set_title("北海道は収量が2.5倍になり、面積の割合も3%から57%に", fontsize=11)
ax.legend(frameon=False, loc="upper left")
fig.tight_layout(); fig.savefig(FIG / "a258_regions.png", dpi=150); plt.close(fig)

# 図3：分解
dcp = res["分解_1958〜67→2015〜24"]
fig, ax = plt.subplots(figsize=(7.2, 3.8))
labs = ["北海道の収量の伸び", "都府県の収量の伸び", "北海道の面積の割合が増えた分"]
vals = [dcp["北海道の伸び"], dcp["都府県の伸び"], dcp["面積の割合の変化"]]
ax.barh(labs[::-1], vals[::-1], color=["#90cdf4", "#c05621", "#2b6cb0"][::-1])
for i, v in enumerate(vals[::-1]):
    ax.text(v + 2, i, f"+{v:.0f}kg（{v/dcp['合計']*100:.0f}%）", va="center", fontsize=9)
ax.set_xlim(0, max(vals) * 1.35)
ax.set_xlabel("10a当たり収量の増え方（kg）")
ax.set_title(f"全国の伸び +{dcp['合計']:.0f}kg（1958〜67年平均 → 2015〜24年平均）の内訳", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "a258_decomp.png", dpi=150); plt.close(fig)
print(json.dumps(res, ensure_ascii=False, indent=1))
