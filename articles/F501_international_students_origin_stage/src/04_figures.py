"""図4枚（PNG）。日付などのメタデータは入れない。"""
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager, ticker
from common import ROOT, REGIONS

D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"; F.mkdir(exist_ok=True)
for cand in ["Noto Sans CJK JP", "Noto Sans CJK SC", "IPAexGothic"]:
    if any(cand in f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = cand
        break
plt.rcParams.update({"font.size": 10.5, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e",
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#8a63d2", "#b5b3ad"]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC = "出典：日本学生支援機構「外国人留学生在籍状況調査」（各年5月1日時点）をもとに作成者が加工して作成"
META = {"Software": None}
comma = ticker.FuncFormatter(lambda v, p: f"{v:,.0f}")


def finish(fig, ax, title, src=SRC):
    ax.set_title(title, loc="left", fontsize=12.5, color=INK, pad=12)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.012, src, fontsize=7.8, color=INK2)


def save(fig, name):
    fig.savefig(F / name, dpi=150, metadata=META)
    plt.close(fig)


m = json.load(open(R / "main.json", encoding="utf-8"))
st = pd.read_csv(D / "stage.csv", index_col="year").loc[2011:2025]

# ---- 図1：在学段階別（積み上げ） ----
fig, ax = plt.subplots(figsize=(8.8, 5.2))
cols = [("grad", "大学院"), ("ug_jc_tech", "学部・短大・高専"), ("prep", "準備教育課程"), ("senshu", "専修学校（専門課程）"), ("jls", "日本語教育機関")]
ax.stackplot(st.index, *[st[k] for k, _ in cols], labels=[l for _, l in cols], colors=[C[0], C[5], C[6], C[3], C[1]], alpha=0.9)
for y in [2019, 2022, 2025]:
    ax.annotate(f"{int(st.total[y]):,}人", (y, st.total[y]), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=9.3, color=INK)
ax.set_xlim(2011, 2025.8)
ax.set_ylim(0, 460000)
ax.set_xlabel("年（各年5月1日）")
ax.set_ylabel("留学生数（人）")
ax.yaxis.set_major_formatter(comma)
ax.grid(axis="y", color=GRID, lw=0.8)
h, l = ax.get_legend_handles_labels()
ax.legend(h[::-1], l[::-1], frameon=False, loc="upper left", fontsize=9.5)
finish(fig, ax, f"2019→2025年の増加の{m['senshu_jls_share_of_change_2019_2025']:.0f}%は、専修学校と日本語教育機関")
fig.subplots_adjust(left=0.11, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig1_stage_stack.png")

# ---- 図2：主な国の人数の推移 ----
bc = pd.read_csv(R / "by_country_year.csv")
fig, ax = plt.subplots(figsize=(8.8, 5.2))
for c, col in [("中国", C[0]), ("ネパール", C[1]), ("ベトナム", C[2]), ("ミャンマー", C[3]), ("スリランカ", C[4]), ("韓国", C[5])]:
    g = bc[bc.country == c].sort_values("year")
    ax.plot(g.year, g.n, color=col, lw=2.3, marker="o", ms=3.5)
    ax.text(2025.3, g.n.iloc[-1] + {"スリランカ": 2500, "韓国": -2500}.get(c, 0), f"{c} {g.n.iloc[-1]:,}", va="center", fontsize=9.3, color=col)
ax.set_xlim(2013, 2028.2)
ax.set_xticks(range(2013, 2026, 2))
ax.set_ylim(0, 145000)
ax.set_xlabel("年（各年5月1日）")
ax.set_ylabel("留学生数（人、日本語教育機関を含む）")
ax.yaxis.set_major_formatter(comma)
ax.grid(axis="y", color=GRID, lw=0.8)
cs = m["country"]
finish(fig, ax, f"中国の割合は{cs['中国']['2013']['share']}%→{cs['中国']['2025']['share']}%、ネパールは{m['ratio_2013_2025']['ネパール']:.0f}倍に（2013→2025年）")
fig.subplots_adjust(left=0.11, right=0.97, top=0.89, bottom=0.15)
save(fig, "fig2_country_trend.png")

# ---- 図3：学ぶ場所ごとの出身国の構成（2025年） ----
q = json.load(open(R / "requestion.json", encoding="utf-8"))
t = pd.DataFrame(q["rows"]).set_index("country")
bars = [("日本語教育機関\n（JASSO）", "jasso_jls_share"), ("高等教育機関\n専修学校などを含む（JASSO）", "jasso_he_share"),
        ("大学・大学院の外国人学生\n（学校基本調査）", "gakko_univ_grad_share")]
cl = [("中国", C[0]), ("ネパール", C[1]), ("ベトナム", C[2]), ("ミャンマー", C[3]), ("韓国", C[5])]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
for i, (lab, key) in enumerate(bars):
    left = 0
    for c, col in cl:
        v = t.at[c, key]
        ax.barh(i, v, left=left, color=col, height=0.6, label=c if i == 0 else None)
        if v >= 4:
            ax.text(left + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=9.3, color="white")
        left += v
    ax.barh(i, 100 - left, left=left, color=C[6], height=0.6, label="その他" if i == 0 else None)
ax.set_yticks(range(len(bars))); ax.set_yticklabels([b[0] for b in bars], fontsize=9.5)
ax.invert_yaxis()
ax.set_xlim(0, 100)
ax.set_xlabel("出身国（地域）の割合（%、2025年5月1日）")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=6, fontsize=9.5)
finish(fig, ax, "大学・大学院では中国が半分以上、日本語教育機関ではネパールが最も多い",
       src="出典：日本学生支援機構「外国人留学生在籍状況調査」、文部科学省「学校基本調査」（2025年度）をもとに作成者が加工して作成")
fig.subplots_adjust(left=0.27, right=0.97, top=0.89, bottom=0.25)
save(fig, "fig3_composition_by_place.png")

# ---- 図4：地方別（北から南） ----
order = [r for r, _ in REGIONS]
rg = pd.read_csv(R / "region_2019_2025.csv", index_col=0).loc[order]
fig, ax = plt.subplots(figsize=(8.8, 5.2))
x = range(len(order)); w = 0.38
ax.bar([i - w / 2 for i in x], rg.n_2019, width=w, color=C[6], label="2019年")
ax.bar([i + w / 2 for i in x], rg.n_2025, width=w, color=C[0], label="2025年")
for i, r in enumerate(order):
    ax.text(i + w / 2, rg.n_2025[r] + 2500, f"{rg.share_2025[r]:.1f}%", ha="center", fontsize=8.8, color=INK)
ax.set_xticks(list(x)); ax.set_xticklabels([{"中国": "中国地方"}.get(r, r) for r in order])
ax.set_ylim(0, 235000)
ax.set_ylabel("留学生数（人、事務局本部の所在地で集計）")
ax.yaxis.set_major_formatter(comma)
ax.grid(axis="y", color=GRID, lw=0.8)
ax.legend(frameon=False, loc="upper right")
ax.text(0.99, 0.80, "棒の上の数字は2025年の全体に占める割合", transform=ax.transAxes, ha="right", fontsize=8.8, color=INK2)
finish(fig, ax, f"関東の割合は{rg.share_2019['関東']}%→{rg.share_2025['関東']}%、近畿は{rg.share_2019['近畿']}%→{rg.share_2025['近畿']}%（2019→2025年）")
fig.subplots_adjust(left=0.11, right=0.97, top=0.89, bottom=0.12)
save(fig, "fig4_region.png")
