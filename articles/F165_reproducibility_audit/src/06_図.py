"""図を figures/ に書く。使い方: python src/06_図.py"""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from pathlib import Path
for p in ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"]:
    if Path(p).exists(): fm.fontManager.addfont(p)
plt.rcParams.update({"font.family": "Noto Sans CJK JP", "figure.dpi": 150, "axes.spines.top": False, "axes.spines.right": False})
D, R, F = Path("data"), Path("results"), Path("figures"); F.mkdir(exist_ok=True)
v = pd.read_csv(R / "verdict_clean_env.csv")
CATS = ["そのまま再現", "取得以外は再現", "手順が止まったが数字は一致", "数字がずれた"]
COL = ["#2b6cb0", "#90cdf4", "#cbd5e0", "#dd6b20"]
# 図1 判定の内訳
fig, ax = plt.subplots(figsize=(8, 3.2))
for i, k in enumerate(["看板", "通常"]):
    g = v[v.kind == k]; left = 0
    for c, col in zip(CATS, COL):
        n = (g.verdict == c).sum()
        if n: ax.barh(i, n, left=left, color=col, label=c if i == 0 or k == "通常" and c == "そのまま再現" else None); ax.text(left + n / 2, i, str(n), ha="center", va="center", color="white" if col in ("#2b6cb0", "#dd6b20") else "black")
        left += n
ax.set_yticks([0, 1], ["看板記事 20本", "通常記事 20本"]); ax.invert_yaxis(); ax.set_xlabel("本数")
h, l = ax.get_legend_handles_labels(); d = dict(zip(l, h)); ax.legend([d[c] for c in CATS if c in d], [c for c in CATS if c in d], ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.28), frameon=False)
ax.set_title("40本を新しい環境で最初から動かし直した結果", loc="left"); fig.tight_layout(); fig.savefig(F / "f165_verdict.png"); plt.close()
# 図2 看板記事ごとの結果ファイルの一致
fa = pd.read_csv(D / "compare_clean_env_by_file.csv")
ORDER = ["完全一致", "1e-6以内", "1e-3以内", "1e-2以内", "ずれ", "形が違う"]
LC = ["#2b6cb0", "#4299e1", "#90cdf4", "#f6ad55", "#dd6b20", "#9c4221"]
g = fa[fa.folder.str.startswith("F")]
ct = g.pivot_table(index="folder", columns="level", values="file", aggfunc="count", fill_value=0).reindex(columns=ORDER, fill_value=0)
ct["n"] = ct.sum(axis=1); ct["bad"] = ct[ORDER[3:]].sum(axis=1)
ct = ct.sort_values(["bad", "n"]); share = ct[ORDER].div(ct.n, axis=0)
fig, ax = plt.subplots(figsize=(8, 6)); left = np.zeros(len(ct))
for c, col in zip(ORDER, LC):
    ax.barh(range(len(ct)), share[c], left=left, color=col, label=c); left += share[c].values
ax.set_yticks(range(len(ct)), [f"{i.split('_')[0]}（{n}）" for i, n in zip(ct.index, ct.n)], fontsize=8)
ax.set_xlabel("結果ファイルの割合（かっこ内はファイル数）"); ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.09), frameon=False, fontsize=8)
ax.set_title("看板記事20本：作り直した結果ファイルは元とどこまで一致したか", loc="left", fontsize=11); fig.tight_layout(); fig.savefig(F / "f165_files.png"); plt.close()
# 図3 環境による違い
e = pd.read_csv(R / "env_comparison.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
for j, col in enumerate(["match_A", "match_B"]):
    for i, r in enumerate(e.itertuples()):
        ok = getattr(r, col); ax.scatter(j, i, s=140, marker="o" if ok else "X", color="#2b6cb0" if ok else "#dd6b20")
ax.set_yticks(range(len(e)), [f.split("_")[0] for f in e.folder], fontsize=8); ax.invert_yaxis()
ax.set_xticks([0, 1], [f"新しい環境\n（requirements.txt だけ）\n一致 {e.match_A.sum()}/15", f"書いたときの環境\n\n一致 {e.match_B.sum()}/15"]); ax.set_xlim(-0.6, 1.6)
ax.set_title("同じ15本を2つの環境で動かすと（○一致　×ずれ）", loc="left"); fig.tight_layout(); fig.savefig(F / "f165_env.png"); plt.close()
# 図4 静的な棚卸し
s = pd.read_csv(R / "static_inventory_summary.csv")
s = s[~s.item.isin(["README に再現手順", "requirements.txt あり"])].sort_values("n")
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(s.item, s.flagship, color="#2b6cb0", label="看板記事（160本）"); ax.barh(s.item, s.regular, left=s.flagship, color="#90cdf4", label="通常記事（219本）")
for i, r in enumerate(s.itertuples()): ax.text(r.n + 1, i, f"{r.n}本（{r.share:.0%}）", va="center", fontsize=8)
ax.set_xlabel("本数（379本中）"); ax.legend(frameon=False, loc="lower right"); ax.set_xlim(0, s.n.max() * 1.3)
ax.set_title("379本を動かさずに調べた、再現の妨げになりそうな点", loc="left"); fig.tight_layout(); fig.savefig(F / "f165_static.png"); plt.close()
# 図5 頑健性
rb = pd.read_csv(R / "robustness.csv"); rb = rb[rb.check == "許容誤差・並び順"]
fig, ax = plt.subplots(figsize=(8, 3.4))
ax.bar(range(len(rb)), rb.match, color=["#90cdf4" if "主" not in x else "#2b6cb0" for x in rb.setting])
for i, m in enumerate(rb.match): ax.text(i, m + 0.3, f"{m}/40", ha="center", fontsize=9)
ax.set_xticks(range(len(rb)), [x.replace("・", "\n") for x in rb.setting], fontsize=8); ax.set_ylim(0, 42); ax.set_ylabel("数字が一致した本数")
ax.set_title("「一致」の基準を変えても、40本中33〜35本でほぼ動かない", loc="left"); fig.tight_layout(); fig.savefig(F / "f165_tolerance.png"); plt.close()
print("ok")
