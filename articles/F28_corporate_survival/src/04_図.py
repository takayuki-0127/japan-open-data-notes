import json, numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import RES, FIG

FIG.mkdir(exist_ok=True)
km = pd.read_csv(RES / "km_curves.csv")
C = {"株式会社": "#2f6db3", "合同会社": "#e07b28", "その他（一般社団・NPOなど）": "#3a9a5b", "全体": "#555555"}

# 1 種別の生存曲線
fig, ax = plt.subplots(figsize=(7.2, 4.4))
for g in ["株式会社", "合同会社", "その他（一般社団・NPOなど）"]:
    s = km[(km.by == "種別") & (km.group == g)]
    ax.plot(s.t, s.S * 100, color=C[g], lw=2, label=g); ax.fill_between(s.t, s.lo * 100, s.hi * 100, color=C[g], alpha=.15)
ax.set_xlabel("設立からの年数"); ax.set_ylabel("登記が残っている割合（%）"); ax.set_ylim(85, 100.5); ax.set_xlim(0, 10.5)
ax.set_title("設立した法人の登記が残っている割合（Kaplan–Meier、2015年11月〜2026年9月に設立）", fontsize=10)
ax.grid(alpha=.3); ax.legend(loc="lower left")
fig.tight_layout(); fig.savefig(FIG / "f28_km_kind.png", dpi=150); plt.close()

# 2 設立からの年数ごとの閉鎖率と、期間別のハザード比
hz = pd.read_csv(RES / "yearly_hazard.csv"); hr = pd.read_csv(RES / "hr_by_period.csv")
fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
for g in ["株式会社", "合同会社", "その他（一般社団・NPOなど）"]:
    s = hz[hz.kind == g]; axs[0].plot(s.year, s.hazard * 100, "o-", color=C[g], label=g)
axs[0].set_xlabel("設立から何年目か"); axs[0].set_ylabel("その年に閉鎖した割合（%）"); axs[0].set_title("年数ごとの閉鎖率", fontsize=10); axs[0].grid(alpha=.3); axs[0].legend(fontsize=8)
per = list(dict.fromkeys(hr.period)); x = np.arange(len(per))
for i, g in enumerate(["合同会社", "その他（一般社団・NPOなど）"]):
    s = hr[hr.kind == g].set_index("period").loc[per]
    axs[1].errorbar(x + (i - .5) * .2, s.HR, yerr=[s.HR - s.lo, s.hi - s.HR], fmt="o", color=C[g], capsize=3, label=g)
axs[1].axhline(1, color="k", lw=.8); axs[1].set_xticks(x, per); axs[1].set_xlabel("設立からの期間"); axs[1].set_ylabel("株式会社に対するハザード比")
axs[1].set_title("ハザード比は期間で変わる（比例ハザードの確認）", fontsize=10); axs[1].grid(alpha=.3); axs[1].legend(fontsize=8)
fig.tight_layout(); fig.savefig(FIG / "f28_hazard_period.png", dpi=150); plt.close()

# 3 Cox のハザード比
cs = pd.read_csv(RES / "cox_summary.csv").set_index("covariate")
lab = {"kindj_合同会社": "合同会社（株式会社と比べ）", "kindj_その他（一般社団・NPOなど）": "その他の法人（同）",
       "area_東京23区": "東京23区（政令市以外の市町村と比べ）", "area_政令市": "政令市（同）",
       "region_北海道・東北": "北海道・東北（関東と比べ）", "region_中部": "中部（同）", "region_近畿": "近畿（同）",
       "region_中国・四国": "中国・四国（同）", "region_九州・沖縄": "九州・沖縄（同）", "cohort_c": "設立年が1年遅い"}
o = [k for k in lab]; s = cs.loc[o]
fig, ax = plt.subplots(figsize=(7.4, 4.6)); y = np.arange(len(o))[::-1]
ax.errorbar(s["exp(coef)"], y, xerr=[s["exp(coef)"] - s["exp(coef) lower 95%"], s["exp(coef) upper 95%"] - s["exp(coef)"]], fmt="o", color="#2f6db3", capsize=3)
ax.axvline(1, color="k", lw=.8); ax.set_yticks(y, [lab[k] for k in o]); ax.set_xscale("log"); ax.set_xticks([.7, 1, 1.5, 2], ["0.7", "1", "1.5", "2"])
ax.set_xlabel("ハザード比（95%区間、対数目盛）"); ax.set_title("Cox 比例ハザードモデル（30万法人を無作為抽出）", fontsize=10); ax.grid(alpha=.3, axis="x")
fig.tight_layout(); fig.savefig(FIG / "f28_cox.png", dpi=150); plt.close()

# 4 設立年別・地域別
fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
cm = plt.cm.viridis(np.linspace(0, .9, 10))
for i, c in enumerate(range(2016, 2026)):
    s = km[(km.by == "設立年") & (km.group == str(c))]; tmax = 2026.75 - c - .25
    s = s[s.t <= tmax]; axs[0].plot(s.t, s.S * 100, color=cm[i], lw=1.6, label=str(c))
axs[0].set_ylim(88, 100.5); axs[0].set_xlabel("設立からの年数"); axs[0].set_ylabel("登記が残っている割合（%）"); axs[0].set_title("設立年ごと：ほとんど重なる", fontsize=10); axs[0].legend(fontsize=7, ncol=2); axs[0].grid(alpha=.3)
for g, col in [("東京23区", "#c0392b"), ("政令市", "#8e44ad"), ("その他の市町村", "#2f6db3")]:
    s = km[(km.by == "地域") & (km.group == g)]; axs[1].plot(s.t, s.S * 100, color=col, lw=2, label=g)
axs[1].set_ylim(85, 100.5); axs[1].set_xlabel("設立からの年数"); axs[1].set_title("本店の場所ごと", fontsize=10); axs[1].legend(); axs[1].grid(alpha=.3)
fig.tight_layout(); fig.savefig(FIG / "f28_cohort_area.png", dpi=150); plt.close()

# 5 全法人の年別の設立と閉鎖
yc = pd.read_csv(RES / "yearly_counts.csv").set_index("year").loc[2016:2025]
fig, axs = plt.subplots(1, 2, figsize=(10, 4.2))
axs[0].plot(yc.index, yc["new"] / 1e4, "o-", color="#2f6db3", label="新しく設立（株式・合同・その他）")
axs[0].plot(yc.index, yc["close"] / 1e4, "o-", color="#c0392b", label="登記の閉鎖（同）")
axs[0].set_ylabel("万法人"); axs[0].set_title("設立と閉鎖の数（年）", fontsize=10); axs[0].legend(fontsize=8); axs[0].grid(alpha=.3)
b = np.zeros(len(yc))
for k, lab2, col in [("01", "清算の結了など", "#7f8c8d"), ("21", "登記官による閉鎖（休眠会社の整理など）", "#e07b28"), ("11", "合併による解散", "#3a9a5b")]:
    axs[1].bar(yc.index, yc[k] / 1e4, bottom=b, color=col, label=lab2); b += yc[k].values / 1e4
axs[1].set_title("閉鎖の事由（すべての法人種別）", fontsize=10); axs[1].set_ylabel("万法人"); axs[1].legend(fontsize=8); axs[1].grid(alpha=.3, axis="y")
fig.tight_layout(); fig.savefig(FIG / "f28_yearly.png", dpi=150); plt.close()
print("figs ok")
