"""図を作る（県・市区町村の名前は出さない）。"""
import json, numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, FIG

COL = {"北海道・東北": "#4C78A8", "関東": "#F58518", "中部": "#54A24B", "近畿": "#E45756", "中国・四国": "#72B7B2", "九州・沖縄": "#B279A2"}
s = json.load(open(RES / "summary.json"))

# 1. モデルによる倍率と95%区間
hr = pd.read_csv(RES / "hr_by_model.csv")
models = ["独立（通常のSE）", "独立（県で束ねた頑健SE）", "県のガンマ・フレイル", "県の対数正規フレイル", "県の固定効果"]
mc = ["#999999", "#555555", "#E45756", "#F58518", "#4C78A8"]
terms = list(dict.fromkeys(hr.term))
fig, ax = plt.subplots(figsize=(8.5, 5.6))
for ti, t in enumerate(terms):
    for mi, m in enumerate(models):
        r = hr[(hr.term == t) & (hr.model == m)].iloc[0]
        y = ti * 6 + mi
        ax.errorbar(r.hr, y, xerr=[[r.hr - r.lo], [r.hi - r.lo - (r.hr - r.lo)]], fmt="o", color=mc[mi], ms=5, capsize=2, label=m if ti == 0 else None)
ax.set_yticks([ti * 6 + 2 for ti in range(len(terms))]); ax.set_yticklabels(terms)
ax.invert_yaxis(); ax.axvline(1, color="k", lw=0.6)
ax.set_xscale("log"); ax.set_xticks([1, 1.2, 1.5, 2]); ax.set_xticklabels(["1", "1.2", "1.5", "2"])
ax.set_xlabel("閉鎖しやすさの倍率（ハザード比、95%区間）")
ax.set_title("県のばらつきを入れると、東京23区の倍率は1.57→1.43に下がり、区間は約2.7倍に広がる", fontsize=10.5)
ax.legend(fontsize=8, loc="lower right"); fig.tight_layout(); fig.savefig(FIG / "f106_hr_models.png", dpi=130); plt.close()

# 2. 県の倍率（経験ベイズ）
p = pd.read_csv(RES / "pref_eb.csv").sort_values("eb").reset_index(drop=True)
fig, ax = plt.subplots(figsize=(8.5, 4.6))
for i, r in p.iterrows():
    ax.plot([i, i], [r.eb_lo, r.eb_hi], color=COL[r.region], lw=1.6)
    ax.plot(i, r.eb, "o", color=COL[r.region], ms=5)
    ax.plot(i, r.raw, "x", color="#333333", ms=4)
for k, v in COL.items(): ax.plot([], [], "o", color=v, label=k)
ax.plot([], [], "x", color="#333333", label="縮める前（実績÷期待）")
ax.axhline(1, color="k", lw=0.6); ax.set_xticks([])
ax.set_xlabel("47都道府県（倍率の小さい順。名前は出していない）"); ax.set_ylabel("閉鎖しやすさの県の倍率 z")
ax.set_title(f"種別・地域区分・設立年をそろえても、県の倍率は {p.eb.min():.2f}〜{p.eb.max():.2f} 倍に分かれる（θ={s['pref_gamma']['theta']:.3f}）", fontsize=10.5)
ax.legend(fontsize=7.5, ncol=4, loc="upper left"); fig.tight_layout(); fig.savefig(FIG / "f106_pref_eb.png", dpi=130); plt.close()

# 3. 単位・設定ごとのフレイルの大きさ
dec = pd.read_csv(RES / "variance_decomposition.csv"); rob = pd.read_csv(RES / "robustness.csv")
lab = list(dec.setting) + ["—"] + list(rob.setting[1:])
val = list(dec.sd) + [np.nan] + list(rob.sd[1:])
fig, ax = plt.subplots(figsize=(8.5, 5.4))
y = np.arange(len(lab))
colors = ["#4C78A8"] * len(dec) + ["w"] + ["#999999"] * (len(rob) - 2) + ["#C9A227"]
ax.barh(y, np.nan_to_num(val), color=colors)
for yi, v in zip(y, val):
    if not np.isnan(v): ax.text(v + 0.003, yi, f"{v:.2f}（τ={v**2 / (v**2 + 2):.3f}）", va="center", fontsize=8)
ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=8.5); ax.invert_yaxis()
ax.set_xlabel("フレイル z の標準偏差（0.16＝平均から±16%ほど）、τ＝同じグループの2社の連動")
ax.set_title("フレイルの大きさ（上：まとめる単位／下：県で設定を変えたもの）", fontsize=10.5)
ax.set_xlim(0, 0.27); fig.tight_layout(); fig.savefig(FIG / "f106_variance.png", dpi=130); plt.close()

# 4. 市区町村の縮め方
m = pd.read_csv(RES / "muni_eb.csv")
fig, ax = plt.subplots(1, 2, figsize=(9.5, 4.2), sharey=True)
for a, col, t in [(ax[0], "raw", "縮める前（実績÷期待）"), (ax[1], "eb", "経験ベイズで縮めたあと")]:
    v = m[col].clip(lower=0.03, upper=30)
    a.scatter(m.E, v, s=5, alpha=0.4, color="#4C78A8")
    a.set_xscale("log"); a.set_yscale("log"); a.axhline(1, color="k", lw=0.6); a.set_ylim(0.02, 40)
    a.set_yticks([0.03, 0.1, 0.3, 1, 3, 10, 30]); a.set_yticklabels(["0", "0.1", "0.3", "1", "3", "10", "30+"])
    a.set_xlabel("その市区町村で期待される閉鎖の数（規模）"); a.set_title(t, fontsize=10)
ax[0].set_ylabel("閉鎖しやすさの倍率")
fig.suptitle(f"小さい市区町村の極端な値は、ほとんどが偶然：期待10件未満の{s['muni_eb']['n_small']}市区町村で、ばらつき（対数のSD）は{s['muni_eb']['raw_sd_small']:.2f}→{s['muni_eb']['eb_sd_small']:.2f}", fontsize=10)
fig.tight_layout(); fig.savefig(FIG / "f106_muni_shrink.png", dpi=130); plt.close()

# 5. 安定性
st = pd.read_csv(RES / "stability_pref.csv"); ss = s["stability"]
fig, ax = plt.subplots(1, 2, figsize=(9.5, 4.3))
for a, (x, y, xl, yl, r) in zip(ax, [("early", "late", "2015〜2019年に設立した法人", "2020〜2026年に設立した法人", ss["cohort_pref"]["pearson"]),
                                     ("kk", "other", "株式会社", "合同会社・一般社団・NPOなど", ss["kind_pref"]["pearson"])]):
    for reg_, g in st.groupby("region"): a.scatter(g[x], g[y], color=COL[reg_], s=22, label=reg_)
    lo, hi = 0.6, 1.6; a.plot([lo, hi], [lo, hi], color="k", lw=0.6, ls="--")
    a.set_xscale("log"); a.set_yscale("log"); a.set_xlim(lo, hi); a.set_ylim(lo, hi)
    tk = [0.7, 0.8, 1.0, 1.2, 1.4]
    a.set_xticks(tk); a.set_xticklabels(tk); a.set_yticks(tk); a.set_yticklabels(tk); a.minorticks_off()
    a.set_xlabel(f"{xl}の県の倍率"); a.set_ylabel(f"{yl}の県の倍率"); a.set_title(f"相関 {r:.2f}", fontsize=10)
ax[0].text(0.62, 1.5, "設立後5年までで比較", fontsize=8)
ax[1].legend(fontsize=7, loc="lower right")
fig.suptitle("県の倍率は、設立した時期や法人の種類を変えてもおおむね同じ県で高い", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "f106_stability.png", dpi=130); plt.close()
print("ok")
