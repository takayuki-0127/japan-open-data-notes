"""市区町村の女性の労働力率を左右しているものを回帰で調べる。
入力: data/processed/municipal_women_labor.csv（src/build_dataset.py で作成）
出力: figures/*.png, data/processed/regression_*.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
PROC = ROOT / "data" / "processed"

# --- 見た目（明るい背景・細い線・グリッドは控えめ） ---
for f in font_manager.findSystemFonts():
    if "NotoSansCJK-Regular" in f:
        font_manager.fontManager.addfont(f)
plt.rcParams.update({
    "font.family": ["Noto Sans CJK JP", "IPAexGothic", "Yu Gothic", "Meiryo", "sans-serif"],
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "axes.edgecolor": "#c9c8c2", "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
    "axes.grid": True, "grid.color": "#ebeae6", "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 11, "axes.titlesize": 13,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "figure.dpi": 150,
})
BLUE, ORANGE, GRAY, INK = "#2a78d6", "#eb6834", "#a3a29c", "#0b0b0b"
SOURCE = "出典：政府統計の総合窓口(e-Stat) 社会・人口統計体系 市区町村データ を加工して作成"

LABELS = {
    "w_old_share": "65歳以上の女性の割合",
    "primary_share": "第1次産業（農林漁業）で働く人の割合",
    "nuclear_share": "核家族世帯の割合",
    "child_share": "0〜5歳の子どもの割合",
    "childcare_per_child": "保育所・こども園に通う子どもの割合",
    "log_density": "人口密度（可住地、対数）",
    "log_income": "納税者1人あたり所得（対数）",
    "w_commute_out": "女性で他の市区町村へ通勤する人の割合",
    "univ_share": "大学・大学院卒の割合",
    "tertiary_share": "第3次産業で働く人の割合",
}
X = list(LABELS)


def load():
    df = pd.read_csv(PROC / "municipal_women_labor.csv")
    d = df[["code", "name", "pref_name", "pref_code", "A1101", "y_flfp", "nursery_per_1k_child"] + X]
    return d.replace([np.inf, -np.inf], np.nan).dropna(subset=["y_flfp"] + X).copy()


def zscore(d, cols):
    z = d.copy()
    for c in cols:
        z[c] = (d[c] - d[c].mean()) / d[c].std()
    return z


def fit(d, xs, fe=True, weights=None, cluster=False):
    z = zscore(d, xs + ["y_flfp"])
    f = "y_flfp ~ " + " + ".join(xs) + (" + C(pref_code)" if fe else "")
    if weights is not None:
        return smf.wls(f, z, weights=d[weights]).fit(cov_type="HC3")
    if cluster:
        return smf.ols(f, z).fit(cov_type="cluster", cov_kwds={"groups": z["pref_code"]})
    return smf.ols(f, z).fit(cov_type="HC3")


def main():
    d = load()
    print("市区町村数:", len(d))
    m0 = smf.ols("y_flfp ~ w_old_share", zscore(d, ["y_flfp", "w_old_share"])).fit()
    m1, m2 = fit(d, X, fe=False), fit(d, X, fe=True)
    mpref = smf.ols("y_flfp ~ C(pref_code)", d).fit()
    print(f"R2  年齢だけ={m0.rsquared:.3f}  都道府県だけ={mpref.rsquared:.3f}  10変数={m1.rsquared:.3f}  10変数+都道府県={m2.rsquared:.3f}")

    tab = pd.DataFrame({
        "変数": [LABELS[x] for x in X],
        "係数_都道府県なし": m1.params[X].values, "p_都道府県なし": m1.pvalues[X].values,
        "係数_都道府県あり": m2.params[X].values,
        "95%下限": m2.conf_int().loc[X, 0].values, "95%上限": m2.conf_int().loc[X, 1].values,
        "p_都道府県あり": m2.pvalues[X].values,
    }, index=X).round(3)
    tab.to_csv(PROC / "regression_main.csv", encoding="utf-8-sig")
    print(tab.sort_values("係数_都道府県あり").to_string())

    # --- 頑健性チェック ---
    wards = d["code"].between(13101, 13123)
    checks = {
        "基本（都道府県を固定）": fit(d, X),
        "都道府県でまとめた標準誤差": fit(d, X, cluster=True),
        "人口で重みづけ": fit(d, X, weights="A1101"),
        "人口5,000人以上だけ": fit(d[d.A1101 >= 5000], X),
        "東京23区を除く": fit(d[~wards], X),
    }
    X2 = [x if x != "childcare_per_child" else "nursery_per_1k_child" for x in X]
    checks["保育を施設数(2023)に替える"] = fit(d, X2)
    rows = []
    for k, m in checks.items():
        r = {"チェック": k, "n": int(m.nobs)}
        for x in ["w_old_share", "primary_share", "nuclear_share", "childcare_per_child", "nursery_per_1k_child", "log_income", "log_density"]:
            if x in m.params:
                r[x] = f"{m.params[x]:+.2f}{'*' if m.pvalues[x] < 0.05 else ''}"
        rows.append(r)
    rob = pd.DataFrame(rows)
    rob.to_csv(PROC / "regression_robustness.csv", index=False, encoding="utf-8-sig")
    print(rob.to_string())

    # --- 図1：女性の労働力率の分布と、65歳以上の割合との関係 ---
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.scatter(d["w_old_share"] * 100, d["y_flfp"] * 100, s=10, color=BLUE, alpha=0.45, linewidths=0)
    b = np.polyfit(d["w_old_share"] * 100, d["y_flfp"] * 100, 1)
    xs = np.linspace(d["w_old_share"].min() * 100, d["w_old_share"].max() * 100, 50)
    ax.plot(xs, np.polyval(b, xs), color=INK, lw=2)
    r = np.corrcoef(d["w_old_share"], d["y_flfp"])[0, 1]
    ax.set_title("女性の労働力率は、まず「年齢構成」で大きく決まる")
    ax.set_xlabel("15歳以上の女性のうち65歳以上の割合（%）")
    ax.set_ylabel("女性の労働力率（%）")
    ax.text(0.98, 0.95, f"相関係数 r = {r:.2f}\n1点 = 1市区町村（n={len(d):,}）", transform=ax.transAxes,
            ha="right", va="top", color="#52514e", fontsize=10)
    fig.text(0.01, 0.01, SOURCE + "（2020年国勢調査ほか）", fontsize=8, color="#8a8984")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig1_age_vs_flfp.png"); plt.close(fig)

    # --- 図2：係数（都道府県なし と あり） ---
    order = tab.sort_values("係数_都道府県あり").index
    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    y = np.arange(len(order))
    ax.axvline(0, color="#c9c8c2", lw=1)
    ax.errorbar(tab.loc[order, "係数_都道府県あり"], y,
                xerr=[tab.loc[order, "係数_都道府県あり"] - tab.loc[order, "95%下限"],
                      tab.loc[order, "95%上限"] - tab.loc[order, "係数_都道府県あり"]],
                fmt="o", color=BLUE, ms=7, lw=2, capsize=0, label="都道府県の違いを取り除いたモデル（95%信頼区間）")
    ax.scatter(tab.loc[order, "係数_都道府県なし"], y + 0.28, marker="D", s=26, color=ORANGE, label="都道府県の違いを取り除かないモデル", zorder=3)
    ax.set_yticks(y, [LABELS[i] for i in order])
    ax.set_xlabel("標準化係数（その変数が1標準偏差高いとき、労働力率が何標準偏差動くか）")
    ax.set_title("ほかの条件をそろえて比べたときの「効き方」")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    fig.text(0.01, 0.01, SOURCE, fontsize=8, color="#8a8984")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(FIG / "fig2_coefficients.png"); plt.close(fig)

    # --- 図3：年齢構成をそろえたあとの都道府県差 ---
    zz = zscore(d, X + ["y_flfp"])
    mres = smf.ols("y_flfp ~ " + " + ".join([x for x in X]), zz).fit()
    # 都道府県の効果は、年齢構成だけをそろえた残差の平均で見る（読み手に説明しやすいため）
    ma = smf.ols("y_flfp ~ w_old_share", d).fit()
    d["resid_age"] = (d["y_flfp"] - ma.fittedvalues) * 100
    pref = d.groupby("pref_name")["resid_age"].mean().sort_values()
    fig, ax = plt.subplots(figsize=(8, 9))
    colors = [ORANGE if v < 0 else BLUE for v in pref.values]
    ax.barh(pref.index, pref.values, color=colors, height=0.7)
    ax.axvline(0, color="#52514e", lw=1)
    ax.set_title("年齢構成をそろえたあとの、都道府県ごとの差")
    ax.set_xlabel("年齢構成から予想される値との差（%ポイント、市区町村の平均）")
    ax.tick_params(axis="y", labelsize=9)
    ax.grid(axis="y", visible=False)
    fig.text(0.01, 0.005, SOURCE, fontsize=8, color="#8a8984")
    fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(FIG / "fig3_pref_residual.png"); plt.close(fig)

    # --- 図4：核家族の割合・保育の利用（ほかの条件をそろえた部分の関係） ---
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
    for ax, x, title in zip(axes, ["nuclear_share", "childcare_per_child"],
                            ["核家族の割合が高いほど、低い", "保育の利用が多いほど、少し高い"]):
        others = [c for c in X if c != x]
        f_y = "y_flfp ~ " + " + ".join(others) + " + C(pref_code)"
        f_x = f"{x} ~ " + " + ".join(others) + " + C(pref_code)"
        ry = smf.ols(f_y, d).fit().resid * 100
        rx = smf.ols(f_x, d).fit().resid * 100
        ax.scatter(rx, ry, s=9, color=BLUE, alpha=0.4, linewidths=0)
        bb = np.polyfit(rx, ry, 1)
        xx = np.linspace(np.percentile(rx, 1), np.percentile(rx, 99), 50)
        ax.plot(xx, np.polyval(bb, xx), color=INK, lw=2)
        ax.set_xlim(np.percentile(rx, 0.5), np.percentile(rx, 99.5)); ax.set_ylim(np.percentile(ry, 0.5), np.percentile(ry, 99.5))
        ax.set_title(title, fontsize=12)
        ax.set_xlabel(f"{LABELS[x]}\n（ほかの条件で説明できない部分、%ポイント）", fontsize=10)
        ax.set_ylabel("女性の労働力率（同上）")
        ax.text(0.98, 0.04, f"傾き {bb[0]:+.3f}", transform=ax.transAxes, ha="right", color="#52514e", fontsize=10)
    fig.text(0.01, 0.01, SOURCE + "（保育は2017年度、ほかは2020年など）", fontsize=8, color="#8a8984")
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(FIG / "fig4_partial_nuclear_childcare.png"); plt.close(fig)

    # 本文で使う数字
    top = d.sort_values("y_flfp", ascending=False)[["pref_name", "name", "y_flfp"]].head(5)
    low = d.sort_values("y_flfp")[["pref_name", "name", "y_flfp"]].head(5)
    print(top.to_string(), low.to_string(), sep="\n")
    print("pref top/bottom", pref.tail(5).round(2).to_dict(), pref.head(5).round(2).to_dict())
    sd = d[X + ["y_flfp"]].std()
    print("SD", sd.round(4).to_dict())


if __name__ == "__main__":
    main()
