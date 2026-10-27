"""F38 図：figures/f38_*.png"""
import json
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from common import RES, FIG

plt.rcParams.update({"font.family": "Noto Sans CJK JP", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150})
C = {"direct": "#2b6cb0", "first": "#68a5e0", "second": "#b7d4f2", "leak": "#d9822b", "grey": "#9aa5b1"}
S = json.load(open(RES / "summary.json", encoding="utf-8"))
toc = lambda v: v / 1000  # 十億円→兆円

# 1 1兆円の行き先（滝グラフ）
fig, ax = plt.subplots(figsize=(8, 4.4))
steps = [("訪日客の消費\n（購入者価格）", 0, 1.0, C["grey"]),
         ("輸入品に\n回った分", 1.0 - toc(S["輸入に漏れた分"]), toc(S["輸入に漏れた分"]), C["leak"]),
         ("国内の直接の\n需要（直接効果）", 0, toc(S["直接効果"]), C["direct"]),
         ("1次波及\n（取引の連鎖）", toc(S["直接効果"]), toc(S["1次波及"]), C["first"]),
         ("2次波及\n（給料からの消費）", toc(S["直接効果"] + S["1次波及"]), toc(S["2次波及"]), C["second"]),
         ("生産の増加\n合計", 0, toc(S["生産誘発_合計"]), "#1a365d")]
for i, (lab, b, h, c) in enumerate(steps):
    ax.bar(i, h, bottom=b, color=c, width=0.62)
    ax.text(i, b + h + 0.03, f"{h:.2f}兆円", ha="center", fontsize=9)
ax.set_xticks(range(len(steps))); ax.set_xticklabels([s[0] for s in steps], fontsize=8)
ax.set_ylabel("兆円"); ax.set_ylim(0, 2.45)
ax.set_title(f"訪日客の消費1兆円で、日本全体の生産は{toc(S['生産誘発_合計']):.2f}兆円増える（2020年表、2次波及まで）", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f38_waterfall.png"); plt.close(fig)

# 2 部門別の生産誘発（上位15）
d = pd.read_csv(RES / "by_sector_2020.csv").head(15).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 5.6))
y = np.arange(len(d))
ax.barh(y, d["直接効果"], color=C["direct"], label="直接効果")
ax.barh(y, d["1次波及"], left=d["直接効果"], color=C["first"], label="1次波及")
ax.barh(y, d["2次波及"], left=d["直接効果"] + d["1次波及"], color=C["second"], label="2次波及")
ax.set_yticks(y); ax.set_yticklabels([n[:14] for n in d["部門"]], fontsize=8.5)
ax.set_xlabel("生産の増加（十億円）")
ax.legend(fontsize=8, loc="lower right", frameon=False)
ax.set_title("増える生産の上位15部門：宿泊・商業・飲食のあとに、食料品や事業所向けサービスが続く", loc="left", fontsize=10.5)
fig.tight_layout(); fig.savefig(FIG / "f38_sectors.png"); plt.close(fig)

# 3 費目ごとに1兆円使った場合
c = pd.read_csv(RES / "by_category_2020.csv")
c = c[c["費目"] != "その他"].reset_index(drop=True)
fig, axs = plt.subplots(1, 2, figsize=(9, 3.9))
cols = ["#2b6cb0"] * len(c)
axs[0].bar(c["費目"], c["波及倍率"], color=cols)
for i, v in enumerate(c["波及倍率"]):
    axs[0].text(i, v + 0.03, f"{v:.2f}倍", ha="center", fontsize=9)
axs[0].set_ylim(0, 2.8); axs[0].set_title("生産の増加（1兆円あたり、倍）", loc="left", fontsize=10)
axs[1].bar(c["費目"], c["雇用誘発_人"] / 1e4, color="#6b8e23")
for i, v in enumerate(c["雇用誘発_人"] / 1e4):
    axs[1].text(i, v + 0.3, f"{v:.1f}", ha="center", fontsize=9)
axs[1].set_ylim(0, 37); axs[1].set_title("雇用（1兆円あたり、万人）", loc="left", fontsize=10)
for ax in axs:
    ax.tick_params(axis="x", labelsize=8.5)
fig.suptitle("同じ1兆円でも、飲食・宿泊に使うのと買物に使うのでは波及が違う", x=0.01, ha="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f38_category.png"); plt.close(fig)

# 4 雇用の誘発（上位12部門）
d = pd.read_csv(RES / "by_sector_2020.csv").sort_values("雇用誘発_人", ascending=False).head(12).iloc[::-1]
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.barh(np.arange(len(d)), d["雇用誘発_人"] / 1e4, color="#6b8e23")
for i, v in enumerate(d["雇用誘発_人"] / 1e4):
    ax.text(v + 0.05, i, f"{v:.1f}", va="center", fontsize=8.5)
ax.set_yticks(np.arange(len(d))); ax.set_yticklabels([n[:14] for n in d["部門"]], fontsize=8.5)
ax.set_xlabel("雇用（万人）")
ax.set_title(f"1兆円で生まれる雇用は約{S['雇用誘発_人']/1e4:.1f}万人分。6割が飲食・宿泊・商業", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f38_employment.png"); plt.close(fig)

# 5 前提で倍率はどれだけ変わるか
r = pd.read_csv(RES / "robustness.csv")
lab = {"基本（2020年表・競争輸入型・2次まで・消費転換0.6）": "基本（2次まで）",
       "2次波及を含めない": "2次波及を含めない",
       "消費転換係数0.5": "消費転換係数 0.5", "消費転換係数0.7": "消費転換係数 0.7",
       "輸入を考えない（閉鎖型）": "輸入を考えない",
       "買物代を生産者価格に直さない": "買物代のマージンを分けない",
       "費目の対応のさせ方を変える（別案）": "費目の対応を変える",
       "輸入を考えない＋生産者価格に直さない＋2次まで（最大）": "輸入なし＋マージン分けない",
       "2015年表": "2015年表"}
r["ラベル"] = r["設定"].map(lab)
r = r.sort_values("波及倍率")
fig, ax = plt.subplots(figsize=(8, 4.6))
colr = ["#d9822b" if "輸入" in s else ("#1a365d" if s == "基本（2次まで）" else "#68a5e0") for s in r["ラベル"]]
ax.barh(r["ラベル"], r["波及倍率"], color=colr)
for i, v in enumerate(r["波及倍率"]):
    ax.text(v + 0.02, i, f"{v:.2f}", va="center", fontsize=9)
ax.set_xlim(0, 3.1); ax.set_xlabel("生産の増加 ÷ 消費額（倍）")
ax.set_title("同じ1兆円でも、前提の置き方で「経済効果」は1.7〜2.8倍まで変わる", loc="left", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "f38_assumptions.png"); plt.close(fig)
print("figs ok")
