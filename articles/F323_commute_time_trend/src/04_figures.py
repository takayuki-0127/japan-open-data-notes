"""04 図：fig1〜fig4（PNG、日付などのメタデータなし）。"""
import json, pathlib
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"; FIG.mkdir(exist_ok=True)
RES = ROOT / "results"
p = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if pathlib.Path(p).exists():
    fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": "#e6e5e0",
                     "grid.linewidth": 0.6, "axes.axisbelow": True})
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK2 = "#52514e"
SRC = "出典：総務省「社会生活基本調査」（令和3年 第6表、平成28年 第68-1表、令和3年 第74-1表）をもとに作成者が加工して作成"
M = json.load(open(RES / "main.json", encoding="utf-8"))
TK = [11, 12, 13, 14]

def save(fig, name, note=""):
    fig.text(0.01, 0.01, SRC + ("\n" + note if note else ""), fontsize=7, color=INK2, ha="left", va="bottom")
    fig.savefig(FIG / name, dpi=150, metadata={"Software": None})
    plt.close(fig)

# fig1 全国の推移
T = pd.read_csv(RES / "national_trend.csv").set_index("year")
fig, ax = plt.subplots(figsize=(8, 4.6))
for col, lab, c, lw in [("総数_平日", "平日（男女計）", C[1], 2.2), ("総数_週全体", "週全体（男女計）", C[0], 2.2),
                        ("男_平日", "平日・男", C[1], 1.0), ("女_平日", "平日・女", C[1], 1.0)]:
    ls = "-" if lw > 1.5 else (":" if "女" in col else "--")
    ax.plot(T.index, T[col], color=c, lw=lw, ls=ls, marker="o" if lw > 1.5 else None, ms=4, label=lab)
for y in (1986, 2016, 2021):
    ax.annotate(f"{T.loc[y,'総数_平日']:.0f}分", (y, T.loc[y, "総数_平日"]), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8.5, color=INK2)
ax.set_xticks(T.index); ax.set_ylim(0, 80)
ax.set_ylabel("通勤・通学の総平均時間（分／日）"); ax.set_xlabel("調査年")
ax.set_title("働く人の通勤時間は2016年まで伸び、2021年に5分縮んだ", loc="left")
ax.legend(frameon=False, ncol=2, fontsize=8.5, loc="lower right")
fig.subplots_adjust(bottom=0.19, left=0.1, right=0.98, top=0.9)
save(fig, "fig1_national_trend.png", "有業者。総平均時間は、通勤しなかった日・人も0分として含めた平均")

# fig2 県別（北から南）
W = pd.read_csv(RES / "pref_change_regular_weekday.csv")
W = W[W.pref > 0].sort_values("pref")
fig, ax = plt.subplots(figsize=(8, 9.2))
y = np.arange(len(W))[::-1]
ax.hlines(y, W["2016"], W["2021"], color="#c3c2b7", lw=1.5)
ax.plot(W["2016"], y, "o", color=C[0], ms=6, label="2016年", mec="#fcfcfb", mew=1)
ax.plot(W["2021"], y, "o", color=C[1], ms=6, label="2021年", mec="#fcfcfb", mew=1)
ax.set_yticks(y, [n if n == "北海道" else n[:-1] for n in W["県"]])
ax.tick_params(axis="y", labelsize=8.5)
ax.set_xlabel("平日の通勤・通学の総平均時間（分、正規の職員・従業員）")
ax.set_title(f"東京圏の4都県は平均{-M['H2']['東京圏_平均変化_分']:.0f}分縮み、地方圏はほぼ変わらない（北から南の順）", loc="left", fontsize=10.5)
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.09, left=0.1, right=0.98, top=0.95)
save(fig, "fig2_pref_2016_2021.png")

# fig3 2016年の長さと変化
fig, ax = plt.subplots(figsize=(8, 5))
q = W.copy()
is_tk = q.pref.isin(TK)
ax.scatter(q.loc[~is_tk, "2016"], q.loc[~is_tk, "変化"], s=30, color=C[0], label="ほかの道府県", edgecolor="#fcfcfb")
ax.scatter(q.loc[is_tk, "2016"], q.loc[is_tk, "変化"], s=45, color=C[1], label="東京圏（埼玉・千葉・東京・神奈川）", edgecolor="#fcfcfb")
for _, rr in q[is_tk].iterrows():
    ax.annotate(rr["県"], (rr["2016"], rr["変化"]), xytext=(5, 3), textcoords="offset points", fontsize=8.5, color=INK2)
b = np.polyfit(q["2016"], q["変化"], 1); xs = np.linspace(q["2016"].min(), q["2016"].max(), 50)
ax.plot(xs, b[0] * xs + b[1], color=INK2, lw=1, ls="--")
ax.axhline(0, color="#0b0b0b", lw=0.8)
ax.set_xlim(44, 110)
ax.set_xlabel("2016年の平日の通勤・通学時間（分、正規の職員・従業員）")
ax.set_ylabel("2016→2021年の変化（分）")
ax.set_title(f"2016年に通勤が長かった県ほど大きく縮んだ（r = {M['H3']['ピアソン_r']:.2f}）", loc="left")
ax.legend(frameon=False, loc="lower left", fontsize=8.5)
fig.subplots_adjust(bottom=0.17, left=0.1, right=0.98, top=0.9)
save(fig, "fig3_level_vs_change.png", f"破線は回帰直線。県を単位にしたブートストラップ（2,000回）の95%区間 r = {M['H3']['r_95%区間'][0]:.2f}〜{M['H3']['r_95%区間'][1]:.2f}")

# fig4 問い直し：構成の変化
c = M["問い直し"]["週全体"]
fig, ax = plt.subplots(figsize=(8, 4.4))
labs = ["有業者総数の変化", "うち 正規の割合が増えた分", "うち 区分の中で縮んだ分"]
vals = [c["有業者総数の変化_分"], c["構成の寄与_分"], c["区分の中の変化の寄与_分"]]
cols = [INK2, C[2], C[1]]
ax.barh(np.arange(3)[::-1], vals, color=cols, height=0.55)
for i, v in enumerate(vals):
    ax.text(v + (0.15 if v >= 0 else -0.15), 2 - i, f"{v:+.1f}分", va="center", ha="left" if v >= 0 else "right", fontsize=9, color=INK2)
ax.set_yticks(np.arange(3)[::-1], labs)
ax.axvline(0, color="#0b0b0b", lw=0.8); ax.set_xlim(-7.5, 2)
ax.set_xlabel("2016→2021年の通勤・通学の総平均時間の変化（分／日、全国・週全体）")
ax.set_title("働き方の構成の変化は、むしろ通勤時間を押し上げる向きだった", loc="left")
ax.grid(axis="y", visible=False)
fig.subplots_adjust(bottom=0.2, left=0.28, right=0.98, top=0.9)
save(fig, "fig4_composition.png", f"有業者を「正規の職員・従業員」（{c['正規の割合_2016_%']:.1f}%→{c['正規の割合_2021_%']:.1f}%）と「それ以外」（総数から逆算）の2つに分けた")
print("figures ok")
