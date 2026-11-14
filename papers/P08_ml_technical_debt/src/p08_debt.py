"""P08 Hidden Technical Debt（Sculley ら 2015）の負債の種類を、このリポジトリの3つの仕組みに当てはめた表を集計し、図にする。
当てはめは data/debts.csv（根拠つき）に手で付けた。
使い方: cd src && python p08_debt.py
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
d = pd.read_csv(HERE / "data" / "debts.csv")
debts = list(dict.fromkeys(d.debt)); projs = list(dict.fromkeys(d.project))
cnt = d.groupby(["project", "status"]).size().unstack(fill_value=0).reindex(projs)
cnt.to_csv(R / "status_counts.csv", encoding="utf-8")
json.dump({p: {k: int(v) for k, v in cnt.loc[p].items()} for p in projs}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
col = {"対応": "#1f5f8b", "一部": "#9bb7cf", "未対応": "#e0a08a", "対象外": "#f0f0f0"}
fig, ax = plt.subplots(figsize=(10, 5.2), dpi=120)
for i, db in enumerate(debts):
    for j, p in enumerate(projs):
        st = d[(d.debt == db) & (d.project == p)].status.iloc[0]
        ax.add_patch(plt.Rectangle((j, i), 0.96, 0.9, color=col[st]))
        ax.text(j + 0.48, i + 0.45, st, ha="center", va="center", fontsize=9, color="white" if st == "対応" else "#333")
ax.set_xlim(0, len(projs)); ax.set_ylim(len(debts), 0)
ax.set_xticks([j + 0.48 for j in range(len(projs))], projs); ax.xaxis.tick_top()
ax.set_yticks([i + 0.45 for i in range(len(debts))], debts, fontsize=9)
for sp in ax.spines.values(): sp.set_visible(False)
ax.tick_params(length=0)
ax.set_title("ML の技術的負債の種類を、このリポジトリの3つの仕組みに当てはめる（手で判定）", fontsize=10.5, pad=28)
fig.tight_layout(); fig.savefig(FG / "p08_01_debts.png"); plt.close(fig)
print(cnt)
