"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = pathlib.Path(__file__).resolve().parent.parent
R = ROOT / "results"; F = ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "IPAexGothic"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand; break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK2, GRID = "#52514e", "#e4e3df"
META = {"Software": None}
SRC = "出典：農林水産省「農業経営統計調査 経営形態別経営統計（個別経営）」をもとに作成者が加工して作成"
M = json.load(open(R / "main.json", encoding="utf-8"))
Q = json.load(open(R / "requestion.json", encoding="utf-8"))
LAB = [("s_farm", C1, "農業（農業所得＋関連事業所得）"), ("s_off", C2, "農外所得（勤め・農業以外の事業など）"), ("s_pen", C3, "年金等の収入")]


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META); plt.close(fig)


def foot(fig, note=""):
    fig.text(0.01, 0.012, (note + "\n" if note else "") + SRC, fontsize=7.6, color=INK2)


# 図1：全国の総所得の内訳（割合）
N = pd.read_csv(R / "national_shares.csv")
fig, ax = plt.subplots(figsize=(8.8, 4.9))
y18 = N.set_index("year").loc[2018]; y04 = N.set_index("year").loc[2004]
cum04 = 0; cum18 = 0
ax.stackplot(N.year, [N[c] for c, _, _ in LAB], colors=[c for _, c, _ in LAB], alpha=0.85, labels=[l for _, _, l in LAB])
for c, col, _ in LAB:
    ax.text(2018.2, cum18 + y18[c] / 2, f"{y18[c]:.0f}%", va="center", fontsize=9.5, color=INK2)
    ax.text(2003.8, cum04 + y04[c] / 2, f"{y04[c]:.0f}%", va="center", ha="right", fontsize=9.5, color=INK2)
    cum18 += y18[c]; cum04 += y04[c]
ax.axvline(M["pension_exceeds_offfarm_first_year"] - 0.5, color="white", lw=1, ls=":")
ax.set_xlim(2003, 2019.2); ax.set_ylim(0, 100); ax.set_ylabel("総所得に占める割合（%）")
ax.set_xticks(range(2004, 2019, 2))
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3, fontsize=9)
ax.set_title(f"農業から来るのは総所得の{y04.s_farm:.0f}%→{y18.s_farm:.0f}%。残りは農外所得と年金（販売農家の平均、全国）", fontsize=11.2, loc="left")
fig.subplots_adjust(bottom=0.24, top=0.9, left=0.08, right=0.95)
foot(fig, f"注：1経営体あたりの平均（名目）。{M['pension_exceeds_offfarm_first_year']}年から年金等の収入が農外所得を上回る。2008年に調査の設計が変わった")
save(fig, "fig1_national_composition.png")

# 図2：主副業別の内訳（2004年と2018年）
S = pd.read_csv(R / "by_type_shares.csv")
fig, ax = plt.subplots(figsize=(8.8, 4.9))
cats = [(t, y) for t in ["主業", "準主業", "副業的"] for y in [2004, 2018]]
xs = []
for i, (t, y) in enumerate(cats):
    x = i + (i // 2) * 0.6; xs.append(x)
    r = S[(S.type == t) & (S.year == y)].iloc[0]
    b = 0
    for c, col, l in LAB:
        ax.bar(x, r[c], bottom=b, color=col, width=0.8, alpha=0.85, label=l if i == 0 else None)
        if r[c] >= 6:
            ax.text(x, b + r[c] / 2, f"{r[c]:.0f}", ha="center", va="center", fontsize=9, color="white")
        b += r[c]
    ax.text(x, 102, f"{r.tot/1000:.1f}百万円", ha="center", fontsize=8, color=INK2)
ax.set_xticks(xs, [f"{t}\n{y}年" for t, y in cats])
ax.set_ylim(0, 110); ax.set_ylabel("総所得に占める割合（%）")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=9)
h = M["H3"]
ax.set_title(f"副業的の農家では、年金が総所得の{h['副業的']['s_pen_2004']:.0f}%→{h['副業的']['s_pen_2018']:.0f}%に（主副業別、全国）", fontsize=11.2, loc="left")
fig.subplots_adjust(bottom=0.28, top=0.9, left=0.08, right=0.97)
foot(fig, "注：棒の上は1経営体あたりの総所得。主業＝農業所得が主で65歳未満の農業従事60日以上の人がいる。副業的＝65歳未満の農業従事60日以上の人がいない")
save(fig, "fig2_by_type.png")

# 図3：都府県の規模別（2004年と2018年）
K = pd.read_csv(R / "by_scale_shares.csv")
KIBO = ["0.5ha未満", "0.5～1.0", "1.0～1.5", "1.5～2.0", "2.0～3.0", "3.0～5.0", "5.0～7.0", "7.0～10.0", "10.0ha以上"]
fig, ax = plt.subplots(figsize=(8.8, 4.9))
x = np.arange(len(KIBO))
for y, col, mk, ls in [(2004, C2, "s", "--"), (2018, C1, "o", "-")]:
    d = K[(K.year == y)].set_index("cls").loc[KIBO]
    ax.plot(x, d.s_farm, color=col, marker=mk, ls=ls, lw=2, label=f"{y}年")
    if y == 2018:
        for i, v in enumerate(d.s_farm):
            ax.text(i, v + (3 if i < len(KIBO) - 1 else -7), f"{v:.0f}", ha="center", fontsize=8.5, color=col)
ax.axhline(50, color=INK2, lw=0.8, ls=":")
ax.text(-0.3, 52, "半分", fontsize=9, color=INK2)
ax.set_xticks(x, ["0.5ha\n未満", "0.5〜\n1.0", "1.0〜\n1.5", "1.5〜\n2.0", "2.0〜\n3.0", "3.0〜\n5.0", "5.0〜\n7.0", "7.0〜\n10.0", "10ha\n以上"], fontsize=9)
ax.set_xlabel("経営耕地の広さ（ha）"); ax.set_ylabel("総所得に占める農業の割合（%）"); ax.set_ylim(0, 100)
ax.legend(frameon=False, loc="upper left")
ax.set_title("農業が総所得の半分を超えるのは3〜5ha から（都府県、2018年）", fontsize=11.5, loc="left")
ax.grid(axis="y", color=GRID); ax.set_axisbelow(True)
fig.subplots_adjust(bottom=0.22, top=0.9, left=0.09, right=0.97)
foot(fig, "注：都府県の販売農家（個別経営）の規模別の平均。北海道は含まない")
save(fig, "fig3_by_scale.png")

# 図4：割合の上がり方の分け方
fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 4.9), gridspec_kw={"width_ratios": [1.3, 1]})
d = M["H2"]
vals = [("農業所得\nの増え", d["farm_up"], C1), ("農外所得\nの減り", d["offfarm_down"], C2), ("年金等\nの増え", d["pension"], C3)]
for i, (l, v, c) in enumerate(vals):
    a1.bar(i, v, color=c, width=0.6, alpha=0.85); a1.text(i, v + (0.3 if v >= 0 else -0.9), f"{v:+.1f}", ha="center", fontsize=9.5, color=INK2)
a1.set_xticks(range(3), [l for l, _, _ in vals]); a1.axhline(0, color=INK2, lw=0.8)
a1.set_ylim(-4, 13); a1.set_ylabel("2004→2018年の農業の割合の変化への寄与（ポイント）")
a1.set_title(f"お金の種類で分ける（計 {d['total']:+.1f}）", fontsize=10.5, loc="left")
vals2 = [("区分の中\nの変化", Q["within"], C1), ("区分の構成\nの変化", Q["composition"], INK2)]
for i, (l, v, c) in enumerate(vals2):
    a2.bar(i, v, color=c, width=0.6, alpha=0.85); a2.text(i, v + (0.3 if v >= 0 else -0.9), f"{v:+.1f}", ha="center", fontsize=9.5, color=INK2)
a2.set_xticks(range(2), [l for l, _, _ in vals2]); a2.axhline(0, color=INK2, lw=0.8); a2.set_ylim(-4, 13)
a2.set_title("主業・準主業・副業的で分ける", fontsize=10.5, loc="left")
for a in (a1, a2):
    a.grid(axis="y", color=GRID); a.set_axisbelow(True)
fig.suptitle("割合が上がったのは主に農業所得の増え。副業的の割合が増えたことは逆向きに効いた", fontsize=11.5, x=0.01, ha="left")
fig.subplots_adjust(bottom=0.2, top=0.86, left=0.1, right=0.98, wspace=0.25)
foot(fig, "注：右は、全国の平均を区分ごとの平均の重みつきの和として表し、重み（構成比）を推定して分けた（推定の構成比は results/requestion_weights.csv）")
save(fig, "fig4_decomposition.png")
print("ok")
