"""04 図：figures/ に PNG を5枚書き出す。"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

for f in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"]:
    if os.path.exists(f):
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
R = os.path.join(ROOT, "results")
F = os.path.join(ROOT, "figures")
os.makedirs(F, exist_ok=True)
SRC = "出典：文部科学省「学校基本調査」、総務省「住民基本台帳人口移動報告」、統計センター「SSDSE-B」を加工して作成"
C1, C2, C3, CG = "#1f5fa8", "#d9822b", "#2e9e6a", "#8a8a8a"
o = json.load(open(os.path.join(R, "results.json"), encoding="utf-8"))
nat = pd.read_csv(os.path.join(R, "national_trend.csv")).replace([np.inf, -np.inf], np.nan)
nat.loc[nat.G == 0, ["r", "r_nonmetro"]] = np.nan

# 図1 全国の推移
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.2))
ax = axes[0]
g = nat[(nat.year >= 2013) & (nat.year <= 2024)]
ax.plot(g.year, g.r * 100, color=C1, marker="o", ms=3, label="全国")
ax.plot(g.year, g.r_nonmetro * 100, color=C2, marker="o", ms=3, label="大都市圏8都府県以外")
ax.set_title("大学入学者 ÷ 高校卒業者（%）", fontsize=11)
ax.set_ylim(40, 75)
ax.legend(fontsize=8)
ax.set_xlabel("年度")
ax = axes[1]
ax.plot(nat.year, nat.o * 100, color=C1, marker="o", ms=3, label="全国")
ax.plot(nat.year, nat.o_nonmetro * 100, color=C2, marker="o", ms=3, label="大都市圏8都府県以外")
ax.plot(nat.year, nat.o_median * 100, color=C3, marker="o", ms=3, label="47都道府県の中央値")
ax.set_title("大学入学者のうち、県外の大学に入った割合（%）", fontsize=11)
ax.set_ylim(45, 80)
ax.legend(fontsize=8)
ax.set_xlabel("年度")
for a in axes: a.xaxis.get_major_locator().set_params(integer=True)
fig.suptitle("大学に進む人は増えたが、県外の大学に入る割合はゆるやかに下がった", fontsize=12)
fig.text(0.01, 0.01, SRC + "。左の分母は過年度卒を含まない高校卒業者なので、100%に近い値ではなく目安", fontsize=7, color="gray")
fig.tight_layout(rect=[0, 0.04, 1, 0.95])
fig.savefig(os.path.join(F, "fig1_trend.png"), dpi=150)
plt.close(fig)

# 図2 分解
dec = o["decomp"]
names = list(dec)
comp = [("G", "高校卒業者数", CG), ("r", "大学に進む多さ", C1), ("o", "県外の大学を選ぶ割合", C2)]
fig, ax = plt.subplots(figsize=(8.4, 4.4))
x = np.arange(len(names))
w = 0.2
for i, (k, lab, c) in enumerate(comp):
    v = [dec[n][k] * 100 for n in names]
    ax.bar(x + (i - 1.5) * w, v, w, color=c, label=lab)
tot = [dec[n]["total"] * 100 for n in names]
ax.bar(x + 1.5 * w, tot, w, color="#333333", label="合計（県外の大学に入った人の数）")
for xi, t in zip(x, tot):
    ax.text(xi + 1.5 * w, t + (1 if t >= 0 else -2.5), f"{t:+.1f}%", ha="center", fontsize=8)
ax.axhline(0, color="black", lw=0.6)
ax.set_xticks(x)
ax.set_xticklabels(names)
ax.set_ylabel("2013→2024年度の変化（対数差×100、%に近い）")
ax.set_title("県外の大学に入る人の数は、進学の増加と卒業者の減少が打ち消し合い、ほぼ横ばい", fontsize=11)
ax.legend(fontsize=8, ncol=2, loc="lower left")
fig.text(0.01, 0.01, SRC, fontsize=7, color="gray")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(os.path.join(F, "fig2_decomposition.png"), dpi=150)
plt.close(fig)

# 図3 県ごとの変化：進学の伸びと 15〜19歳の転入超過の変化
d = pd.read_csv(os.path.join(R, "decomp_by_pref.csv"))
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.3))
for ax, (y, ylab, ttl) in zip(axes, [("dlno", "県外の大学を選ぶ割合の変化（対数差）", "進学はすべての県で伸びたが、7割の県で県外の割合は下がった"),
                                     ("dm15", "15〜19歳の転入超過（高卒者1人あたり）の変化", "進学の伸びと、15〜19歳の転出の変化は無関係に近い")]):
    for mflag, c, lab in [(False, C2, "大都市圏8都府県以外"), (True, C1, "大都市圏8都府県")]:
        s = d[d.metro == mflag]
        ax.scatter(s.dlnr, s[y], s=22, color=c, alpha=0.8, label=lab)
    b = np.polyfit(d.dlnr, d[y], 1)
    xx = np.linspace(d.dlnr.min(), d.dlnr.max(), 10)
    ax.plot(xx, np.polyval(b, xx), color=CG, lw=1)
    ax.axhline(0, color="black", lw=0.5)
    ax.set_xlabel("大学に進む多さの変化（対数差、2013→2024年度）")
    ax.set_ylabel(ylab, fontsize=9)
    ax.set_title(ttl, fontsize=10)
    r = np.corrcoef(d.dlnr, d[y])[0, 1]
    ax.text(0.02, 0.95, f"相関 {r:+.2f}", transform=ax.transAxes, fontsize=9, va="top")
axes[0].legend(fontsize=8, loc="lower right")
fig.text(0.01, 0.01, SRC + "。点は都道府県（名前は表示していない）", fontsize=7, color="gray")
fig.tight_layout(rect=[0, 0.04, 1, 1])
fig.savefig(os.path.join(F, "fig3_pref_change.png"), dpi=150)
plt.close(fig)

# 図4 15〜19歳の転入超過は、大学の入学の出入りの一部しか映していない
cs = pd.read_csv(os.path.join(R, "cross_section_means.csv"))
fig, ax = plt.subplots(figsize=(7.2, 4.6))
METRO = ["埼玉", "千葉", "東京", "神奈川", "愛知", "京都", "大阪", "兵庫"]
mm = cs.pref.isin(METRO)
ax.scatter(cs.netuni_rate[~mm], cs.m15[~mm], color=C2, s=24, label="大都市圏8都府県以外")
ax.scatter(cs.netuni_rate[mm], cs.m15[mm], color=C1, s=24, label="大都市圏8都府県")
lim = [min(cs.netuni_rate.min(), cs.m15.min()) - 0.02, max(cs.netuni_rate.max(), cs.m15.max()) + 0.02]
ax.plot(lim, lim, ls=":", color="black", lw=0.8, label="入学の出入りがそのまま映った場合（45°線）")
b = o["cross_m15_on_netuni"]
xx = np.linspace(cs.netuni_rate.min(), cs.netuni_rate.max(), 10)
fit = np.polyfit(cs.netuni_rate, cs.m15, 1)
ax.plot(xx, np.polyval(fit, xx), color=CG, lw=1.2, label=f"当てはめた直線（傾き {b['b']:.2f}）")
ax.axhline(0, color="black", lw=0.4)
ax.axvline(0, color="black", lw=0.4)
ax.set_xlabel("大学入学の出入り（他県から入る − 県外へ出る）÷ 高卒者")
ax.set_ylabel("15〜19歳の転入超過 ÷ 高卒者")
ax.set_title("住民票の移動に表れるのは、大学入学の出入りの4分の1ほど", fontsize=11)
ax.legend(fontsize=8)
fig.text(0.01, 0.01, SRC + "。2013〜2024年度の平均", fontsize=7, color="gray")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(os.path.join(F, "fig4_netuni_vs_mig.png"), dpi=150)
plt.close(fig)

# 図5 頑健性：固定効果パネルの r（大学に進む多さ）の係数
rows = [("基本（2013〜2024年度）", o["fe_main_r_o"]["r"])]
for k, v in o["robust"].items():
    key = "r_j" if "r_j" in v else "r"
    rows.append((k, v[key]))
fig, ax = plt.subplots(figsize=(7.6, 4.8))
y = np.arange(len(rows))[::-1]
for yi, (lab, v) in zip(y, rows):
    ax.plot([v["lo"], v["hi"]], [yi, yi], color=C1 if lab.startswith("基本") else CG, lw=2)
    ax.plot(v["b"], yi, "o", color=C1 if lab.startswith("基本") else "#333333", ms=5)
ax.axvline(0, color="black", lw=0.7)
ax.set_yticks(y)
ax.set_yticklabels([r[0] for r in rows], fontsize=8)
ax.set_xlabel("大学に進む多さが1（100%ポイント）上がったときの、15〜19歳の転入超過（高卒者1人あたり）の変化")
ax.set_title("どの条件でも、進学の多さの係数は0と区別できなかった", fontsize=11)
ax.xaxis.label.set_size(8)
fig.text(0.01, 0.01, "出典：学校基本調査・住民基本台帳人口移動報告・SSDSE-B を加工。県と年の固定効果、県でクラスターした95%区間", fontsize=7, color="gray")
fig.tight_layout(rect=[0, 0.03, 1, 1])
fig.savefig(os.path.join(F, "fig5_robustness.png"), dpi=150)
plt.close(fig)
print("ok")
