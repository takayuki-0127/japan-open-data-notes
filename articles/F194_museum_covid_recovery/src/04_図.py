"""04 図：figures/ に PNG を5枚書き出す。"""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import statsmodels.api as sm
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "axes.spines.top": False, "axes.spines.right": False})
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, "data"); R = os.path.join(ROOT, "results"); F = os.path.join(ROOT, "figures"); os.makedirs(F, exist_ok=True)
SRC = "出典：文部科学省「社会教育調査」、国土交通省「鉄道輸送統計調査」（いずれも e-Stat）を加工して作成"
C1, C2, C3, CG = "#1f5fa8", "#d9822b", "#2e9e6a", "#8a8a8a"
def foot(fig): fig.text(0.01, 0.005, SRC, fontsize=7, color=CG)

vis = pd.read_csv(os.path.join(D, "national_visitors_by_type.csv")).set_index("fy")
bt = pd.read_csv(os.path.join(R, "recovery_by_type.csv")).set_index("series")
rob = pd.read_csv(os.path.join(R, "robustness_baseline.csv"))
rail = pd.read_csv(os.path.join(R, "rail_fiscal_comparison.csv")).set_index("series")
oth = pd.read_csv(os.path.join(R, "other_facilities.csv")).set_index("facility")
spc = pd.read_csv(os.path.join(R, "special_exhibitions.csv"))
reg = pd.read_csv(os.path.join(R, "recovery_by_region.csv")).set_index("region")
rf = pd.read_csv(os.path.join(D, "rail_fiscal_year.csv"))

# 図1 全国の入館者数（博物館＋類似施設）と、コロナ前の傾向
s = vis["合計"] / 1000  # 百万人
fit = [1998, 2001, 2004, 2007, 2010, 2014, 2017]
m = sm.OLS(np.log(s.loc[fit].values), sm.add_constant(np.array(fit, float))).fit()
xs = np.arange(1998, 2024)
pr = m.get_prediction(sm.add_constant(xs.astype(float))).summary_frame(alpha=0.05)
fig, ax = plt.subplots(figsize=(9, 4.8))
ax.plot(s.index, s.values, "o-", color=C1, lw=2, label="実績（3年ごとの調査）")
ax.plot(xs, np.exp(pr["mean"]), color=C2, ls="--", lw=1.8, label="1998〜2017年度の傾向（年+0.4%）")
ax.fill_between(xs[xs >= 2017], np.exp(pr["obs_ci_lower"])[xs >= 2017], np.exp(pr["obs_ci_upper"])[xs >= 2017], color=C2, alpha=0.15, label="傾向の95%予測区間")
for y in [2020, 2023]:
    ax.annotate(f"{y}年度\n{s[y]:.0f}百万人（2017年度の{s[y]/s[2017]*100:.0f}%）", (y, s[y]), xytext=(-125 if y == 2023 else 10, -40 if y == 2023 else 10), textcoords="offset points", fontsize=9,
                arrowprops=dict(arrowstyle="-", color=CG))
ax.set_ylabel("入館者数（百万人／年度）"); ax.set_ylim(0, 340); ax.set_xlim(1985, 2025)
ax.set_title("博物館・美術館（類似施設を含む）の入館者数：2023年度は2017年度の85%")
ax.legend(loc="lower left", fontsize=9, frameon=False)
foot(fig); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(os.path.join(F, "fig1_national_trend.png"), dpi=150); plt.close(fig)

# 図2 種類別：2023年度÷2017年度 と 傾向比
TY = ["水族館", "動植物園", "総合", "科学", "美術", "動物園", "野外", "歴史", "植物園"]
LB = {"総合": "総合博物館", "科学": "科学博物館", "歴史": "歴史博物館", "美術": "美術博物館", "野外": "野外博物館"}
b = bt.loc[TY]
fig, ax = plt.subplots(figsize=(9, 4.8))
y = np.arange(len(TY))
ax.barh(y, b.vs2017_2023 * 100, color=C1, height=0.55, label="2017年度比")
ax.plot(b.rec2023 * 100, y, "D", color=C2, label="1998〜2017年度の傾向比")
ax.axvline(100, color=CG, lw=1, ls=":")
ax.set_yticks(y); ax.set_yticklabels([f"{LB.get(t, t)}（{bt.loc[t,'fy2017']/1000:.0f}百万人）" for t in TY]); ax.invert_yaxis()
for i, v in enumerate(b.vs2017_2023 * 100):
    ax.text(v + 1, i + 0.25, f"{v:.0f}%", fontsize=9, color=C1)
ax.set_xlim(0, 130); ax.set_xlabel("2023年度の入館者数（%）　（ ）内は2017年度の入館者数")
ax.set_title("種類別：水族館・動植物園は戻り、歴史博物館は77%")
ax.legend(loc="lower right", fontsize=9, frameon=False)
foot(fig); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(os.path.join(F, "fig2_by_type.png"), dpi=150); plt.close(fig)

# 図3 鉄道（F136 と同じ統計）と並べる：2017年度＝100
nat = rf[rf.unit == "全国"].set_index("fy")
fig, ax = plt.subplots(figsize=(9, 4.8))
yrs = list(range(2014, 2026))
ax.plot(yrs, nat.loc[yrs, "teikigai"] / nat.loc[2017, "teikigai"] * 100, "-", color=C3, lw=2, label="鉄道・定期外（毎年度）")
ax.plot(yrs, nat.loc[yrs, "total"] / nat.loc[2017, "total"] * 100, "-", color=CG, lw=1.6, label="鉄道・計（毎年度）")
mus = vis["合計"]
ax.plot([2014, 2017, 2020, 2023], [mus[y] / mus[2017] * 100 for y in [2014, 2017, 2020, 2023]], "o-", color=C1, lw=2.2, label="博物館・美術館（3年ごと）")
for y_ in [2020, 2023]:
    ax.text(y_ + 0.15, mus[y_] / mus[2017] * 100 - 6, f"{mus[y_]/mus[2017]*100:.0f}", color=C1, fontsize=9)
    ax.text(y_ + 0.15, nat.loc[y_, "teikigai"] / nat.loc[2017, "teikigai"] * 100 + 2, f"{nat.loc[y_,'teikigai']/nat.loc[2017,'teikigai']*100:.0f}", color=C3, fontsize=9)
ax.axhline(100, color=CG, lw=1, ls=":")
ax.set_xticks(yrs); ax.set_xticklabels([f"{y}" for y in yrs], fontsize=8)
ax.set_ylabel("2017年度＝100"); ax.set_xlabel("年度"); ax.set_ylim(30, 115)
ax.set_title("2023年度、鉄道の定期外は95%、博物館・美術館は85%")
ax.legend(loc="lower left", fontsize=9, frameon=False)
foot(fig); fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(os.path.join(F, "fig3_vs_rail.png"), dpi=150); plt.close(fig)

# 図4 特別展とそれ以外、ほかの社会教育施設
fig, axs = plt.subplots(1, 2, figsize=(10, 4.8), gridspec_kw=dict(width_ratios=[1, 1.25]))
ax = axs[0]
lab = []; val = []
for kind in ["博物館", "博物館類似施設"]:
    for v, nm in [("visitors", "計"), ("regular", "特別展以外"), ("special", "特別展")]:
        r_ = spc[(spc.kind == kind) & (spc["var"] == v)].iloc[0]
        lab.append(f"{'博物館' if kind=='博物館' else '類似施設'}・{nm}"); val.append(r_.vs2017_2023 * 100)
yy = np.arange(len(lab))
ax.barh(yy, val, color=[C1, C1, C1, C2, C2, C2], alpha=0.9, height=0.55)
for i, v in enumerate(val): ax.text(v + 1, i + 0.2, f"{v:.0f}%", fontsize=9)
ax.set_yticks(yy); ax.set_yticklabels(lab, fontsize=9); ax.invert_yaxis(); ax.axvline(100, color=CG, ls=":", lw=1)
ax.set_xlim(0, 125); ax.set_title("2023年度÷2017年度（特別展の内訳）", fontsize=10)
ax = axs[1]
OF = ["生涯学習センター", "図書館", "博物館", "社会体育施設", "博物館類似施設", "青少年教育施設", "公民館", "女性教育施設"]
o = oth.loc[OF]
yy = np.arange(len(OF))
ax.barh(yy, o.vs2017_2023 * 100, color=[C1 if f.startswith("博物館") else CG for f in OF], height=0.55)
for i, v in enumerate(o.vs2017_2023 * 100): ax.text(v + 1, i + 0.2, f"{v:.0f}%", fontsize=9)
ax.set_yticks(yy); ax.set_yticklabels(OF, fontsize=9); ax.invert_yaxis(); ax.axvline(100, color=CG, ls=":", lw=1)
ax.set_xlim(0, 135); ax.set_title("ほかの社会教育施設の利用者数（2023年度÷2017年度）", fontsize=10)
fig.suptitle("博物館の特別展以外はほぼ戻り、類似施設は78%（施設区分の見直しを含む）", fontsize=12)
foot(fig); fig.tight_layout(rect=(0, 0.03, 1, 0.95)); fig.savefig(os.path.join(F, "fig4_special_and_facilities.png"), dpi=150); plt.close(fig)

# 図5 地方（9区分、地理の順）：博物館・美術館と鉄道の定期外
fig, ax = plt.subplots(figsize=(9, 4.8))
x = np.arange(len(reg)); w = 0.38
ax.bar(x - w/2, reg.vs2017_2023 * 100, w, color=C1, label="博物館・美術館（類似施設を含む）")
ax.bar(x + w/2, reg.rail_teikigai_vs2017_2023 * 100, w, color=C3, label="鉄道・定期外")
for i, (a_, b_) in enumerate(zip(reg.vs2017_2023 * 100, reg.rail_teikigai_vs2017_2023 * 100)):
    ax.text(i - w/2, a_ + 1, f"{a_:.0f}", ha="center", fontsize=8, color=C1); ax.text(i + w/2, b_ + 1, f"{b_:.0f}", ha="center", fontsize=8, color=C3)
ax.axhline(100, color=CG, ls=":", lw=1)
ax.set_xticks(x); ax.set_xticklabels(reg.index, fontsize=9)
ax.set_ylabel("2023年度÷2017年度（%）"); ax.set_ylim(0, 130)
ax.set_title("地方別：博物館の戻り方と鉄道の定期外の戻り方は、そろっていない（順位相関−0.30）")
ax.legend(loc="lower left", fontsize=9, frameon=False)
fig.text(0.01, 0.03, "地方の区分は運輸局（沖縄は九州とまとめた）。鉄道は事業者の所属する運輸局で集計されるため、地域の対応はおおまか。", fontsize=7.5, color=CG)
foot(fig); fig.tight_layout(rect=(0, 0.05, 1, 1)); fig.savefig(os.path.join(F, "fig5_regions.png"), dpi=150); plt.close(fig)
print("ok")
