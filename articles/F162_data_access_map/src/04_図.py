"""04 図（figures/）"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import RES, FIG

for f in font_manager.findSystemFonts():
    if "NotoSansCJK" in f: font_manager.fontManager.addfont(f)
plt.rcParams.update({"font.family": ["Noto Sans CJK JP", "sans-serif"], "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 11, "axes.titlesize": 13, "figure.dpi": 150, "savefig.bbox": "tight"})
FIG.mkdir(exist_ok=True)
SRC = "出典：japan-open-data-notes（コミット 8090888）の各記事の README・取得コードを集計して作成"
G4 = ["API", "ファイル（表・一括）", "画面・ページから", "PDF・手で転記", "経路の記録なし"]
COL = {"API": "#2a78d6", "ファイル（表・一括）": "#8fb8e8", "画面・ページから": "#eb6834", "PDF・手で転記": "#b5401a", "経路の記録なし": "#cfcdc6"}
r = json.load(open(RES / "results.json"))

def stacked(ax, rows, labels):
    left = np.zeros(len(rows))
    for g in G4:
        v = np.array([row[g] for row in rows]) * 100
        ax.barh(range(len(rows)), v, left=left, color=COL[g], label=g, height=0.62, edgecolor="white", linewidth=0.6)
        for i, (l, x) in enumerate(zip(left, v)):
            if x >= 6: ax.text(l + x / 2, i, f"{x:.0f}", ha="center", va="center", fontsize=9.5, color="white" if g in ("API", "画面・ページから", "PDF・手で転記") else "#0b0b0b")
        left += v
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(labels); ax.invert_yaxis(); ax.set_xlim(0, 100); ax.set_xlabel("割合（%）")

# 図1 全体：機械向きの経路で数える／手間のかかる経路で数える
fig, ax = plt.subplots(figsize=(9, 3.0))
stacked(ax, [r["group_share"], r["group_share_hard"]], ["いちばん機械向きの経路で\n数えた場合", "いちばん手間のかかる経路で\n数えた場合"])
ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.26), frameon=False, fontsize=9.5)
ax.set_title(f"新しく取ったデータ {r['n_pairs_new']} 組（記事×統計の作り手）の取り方", loc="left")
fig.text(0, -0.36, SRC, fontsize=8, color="#666")
fig.savefig(FIG / "fig1_overall.png"); plt.close(fig)

# 図2 作り手ごとの地図
own = pd.read_csv(RES / "owner_map.csv", index_col=0)
fig, ax = plt.subplots(figsize=(9.5, 6.4))
stacked(ax, [own.loc[o, G4].to_dict() for o in own.index], [f"{o}（{int(own.loc[o,'n'])}組）" for o in own.index])
for i, o in enumerate(own.index):
    ax.text(101.5, i, f"{own.loc[o,'via_estat']*100:.0f}%", va="center", fontsize=9.5, color="#333")
ax.text(101.5, -0.9, "e-Stat\n経由", fontsize=9, color="#333", va="bottom")
ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.45, -0.08), frameon=False, fontsize=9.5)
ax.set_title("統計の作り手ごとの取り方（新しく取った組が5組以上）", loc="left")
fig.text(0, -0.06, SRC + "。数字は各組の割合（%）", fontsize=8, color="#666")
fig.savefig(FIG / "fig2_owner_map.png"); plt.close(fig)

# 図3 e-Stat 経由かどうか
rob = pd.read_csv(RES / "robustness.csv", index_col=0)
fig, ax = plt.subplots(figsize=(9, 2.9))
keys = ["e-Stat 経由の組だけ", "e-Stat 経由でない組だけ"]
rows = []
for k in keys:
    rows.append({"API": rob.loc[k, "API"], "ファイル（表・一括）": rob.loc[k, "ファイル"], "画面・ページから": rob.loc[k, "手間（画面・PDF・転記）"], "PDF・手で転記": 0, "経路の記録なし": rob.loc[k, "記録なし"]})
stacked(ax, rows, [f"e-Stat 経由（{int(rob.loc[keys[0],'n'])}組）", f"各府省・機関のサイトなど（{int(rob.loc[keys[1],'n'])}組）"])
h = [plt.Rectangle((0, 0), 1, 1, color=COL[g]) for g in ["API", "ファイル（表・一括）", "画面・ページから", "経路の記録なし"]]
ax.legend(h, ["API", "ファイル（表・一括）", "画面・ページ・PDF・転記", "経路の記録なし"], ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.3), frameon=False, fontsize=9.5)
ax.set_title("e-Stat を通した組は、ファイルで取れた割合が高い", loc="left")
fig.text(0, -0.4, SRC, fontsize=8, color="#666")
fig.savefig(FIG / "fig3_estat.png"); plt.close(fig)

# 図4 記事の順番（看板記事 F を番号で3つに分ける）
tf = pd.read_csv(RES / "trend_F.csv", index_col=0)
fig, ax = plt.subplots(figsize=(9, 3.4))
stacked(ax, [tf.loc[p, G4].to_dict() for p in tf.index], [f"F の{p}の3分の1（{int(tf.loc[p,'n'])}組）" for p in tf.index])
ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.24), frameon=False, fontsize=9.5)
ax.set_title("看板記事は、後の番号ほど「ファイルで取れない」データが増えた", loc="left")
fig.text(0, -0.32, SRC, fontsize=8, color="#666")
fig.savefig(FIG / "fig4_trend_F.png"); plt.close(fig)

# 図5 頑健性：分類の仕方を変えたときの割合
fig, ax = plt.subplots(figsize=(9, 4.6))
order = list(rob.index)
cols = [("ファイル", "ファイル（表・一括）", "o"), ("記録なし", "経路の記録なし", "s"), ("手間（画面・PDF・転記）", "画面・ページ・PDF・転記", "D"), ("API", "API", "^")]
ccol = {"ファイル": "#2a78d6", "記録なし": "#7a7870", "手間（画面・PDF・転記）": "#eb6834", "API": "#0b0b0b"}
for c, lab, m in cols:
    ax.scatter(rob[c] * 100, range(len(order)), marker=m, s=46, color=ccol[c], label=lab, zorder=3)
ax.set_yticks(range(len(order))); ax.set_yticklabels([f"{o}（{int(rob.loc[o,'n'])}）" for o in order], fontsize=9.5); ax.invert_yaxis()
ax.set_xlim(0, 100); ax.set_xlabel("割合（%）"); ax.grid(axis="x", color="#e5e4e0", zorder=0)
ax.legend(ncol=4, loc="upper center", bbox_to_anchor=(0.4, -0.13), frameon=False, fontsize=9.5)
ax.set_title("数え方を変えても「ファイルが中心・API はわずか」は同じ", loc="left")
fig.text(0, -0.16, SRC + "。（ ）は組または記事の数", fontsize=8, color="#666")
fig.savefig(FIG / "fig5_robustness.png"); plt.close(fig)
print("ok")
