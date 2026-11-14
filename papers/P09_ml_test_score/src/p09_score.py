"""P09 ML Test Score（Breck ら 2017）の28項目で、youtube-views-predictor を採点する。
点の付け方（論文の決まり）：手で行い結果を記録していれば0.5点、自動で繰り返し行っていれば1点。4つの区分ごとに合計し、最終の点は4つのうち最も低い区分の点。
採点は data/scores.csv（根拠つき）に手で付けた。このスクリプトは集計と図だけ。
使い方: cd src && python p09_score.py
"""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = Path(__file__).resolve().parents[1]
R, FG = HERE / "results", HERE / "figures"
R.mkdir(exist_ok=True); FG.mkdir(exist_ok=True)
s = pd.read_csv(HERE / "data" / "scores.csv")
order = ["データ", "モデル", "仕組み", "見張り"]
tot = s.groupby("section").points.sum().reindex(order)
final = float(tot.min())
band = ("研究の段階に近い" if final == 0 else "テストはあるが、信頼性に大きな穴がありうる" if final <= 1 else
        "本番向けの最初の一歩。さらに手を入れる必要がある" if final <= 2 else "それなりにテストされている" if final <= 3 else "自動のテストと見張りが強い")
main = {"section_totals": {k: float(v) for k, v in tot.items()}, "final_score": final, "band": band,
        "n_half": int((s.points == 0.5).sum()), "n_full": int((s.points == 1).sum()), "n_zero": int((s.points == 0).sum())}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
tot.to_csv(R / "section_totals.csv", encoding="utf-8")

fig, ax = plt.subplots(figsize=(10, 4.6), dpi=120)
cmap = {0: "#eeeeee", 0.5: "#9bb7cf", 1: "#1f5f8b"}
for i, sec in enumerate(order):
    g = s[s.section == sec].sort_values("no")
    for j, (_, r) in enumerate(g.iterrows()):
        ax.add_patch(plt.Rectangle((j, i), 0.95, 0.9, color=cmap[r.points]))
        ax.text(j + 0.47, i + 0.45, f"{r.no}", ha="center", va="center", fontsize=9, color="#333" if r.points < 1 else "white")
    ax.text(7.2, i + 0.45, f"計 {tot[sec]:.1f} 点", va="center", fontsize=10, fontweight="bold" if tot[sec] == final else None)
ax.set_xlim(0, 8.6); ax.set_ylim(len(order), 0)
ax.set_yticks([i + 0.45 for i in range(4)], order); ax.set_xticks([])
for sp in ax.spines.values(): sp.set_visible(False)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=cmap[0], label="0点（していない）"), Patch(color=cmap[0.5], label="0.5点（手でして記録した）"), Patch(color=cmap[1], label="1点（自動で繰り返す）")],
          loc="lower center", bbox_to_anchor=(0.42, -0.2), ncol=3, fontsize=9, frameon=False)
ax.set_title(f"youtube-views-predictor の ML Test Score：最終 {final:.1f} 点（最も低い区分の点）\n28項目のうち 0.5点が {main['n_half']}、0点が {main['n_zero']}。自動で回っているものはまだない", fontsize=10.5)
fig.tight_layout(); fig.savefig(FG / "p09_01_scores.png"); plt.close(fig)
print(json.dumps(main, ensure_ascii=False, indent=1))
