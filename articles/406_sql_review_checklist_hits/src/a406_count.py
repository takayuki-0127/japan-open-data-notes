"""406 SQL の見直しの観点10個を、自分の記事の SQL に当てると何件引っかかるか（その2：数える・図にする）
data/sql_files.csv・data/hits.csv（a406_scan.py が作る）と、data/labels_manual.csv（引っかかった行を読んで付けた分類）を読む。"""
import json
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from common import *
from a406_scan import CHECKS

F = pd.read_csv(DATA / "sql_files.csv"); H = pd.read_csv(DATA / "hits.csv").fillna(""); L = pd.read_csv(DATA / "labels_manual.csv")
key = ["記事", "ファイル", "行番号", "観点"]
# 同じ行に同じ観点が2回当たることがある（1行に SELECT * が2つ、など）。分類は行ごとに1つ
H = H.merge(L.drop_duplicates(key), on=key, how="left")
assert H[H["観点"] != "C06"]["分類"].notna().all()
H["系列"] = np.where(H["記事"].str.startswith("F"), "看板記事（F）", "実務の型など（番号）")
F["系列"] = np.where(F["記事"].str.startswith("F"), "看板記事（F）", "実務の型など（番号）")
names = {c: n for c, n, _ in CHECKS}
ORDER = ["わざと書いた悪い例", "誤検出", "問題なし", "直す候補"]

# ---- 1. 観点ごとの数 ----
rows = []
for c, n, why in CHECKS:
    h = H[H["観点"] == c]
    d = {"観点": c, "名前": n, "心配なこと": why, "引っかかった数": len(h), "ファイルの数": h[["記事", "ファイル"]].drop_duplicates().shape[0], "記事の数": h["記事"].nunique()}
    for o in ORDER: d[o] = int((h["分類"] == o).sum())
    rows.append(d)
T = pd.DataFrame(rows); T.to_csv(RES / "hits_by_check.csv", index=False)
NC = H[H["観点"] != "C06"]

# ---- 2. 割り算（C06）：分母の形と、守りの有無（機械の判定だけ）----
D = H[H["観点"] == "C06"].copy(); D[["分母の形", "守り"]] = D["補足"].str.split("｜", expand=True)
D6 = D.groupby(["分母の形", "守り"]).size().unstack(fill_value=0).reindex(columns=["守りなし", "守りあり"], fill_value=0)
D6["計"] = D6.sum(1); D6 = D6.sort_values("計", ascending=False); D6.to_csv(RES / "division_by_denominator.csv")
bad6 = int(D["直前のコメント"].str.contains(r"\[bad\]", regex=True).sum())

# ---- 3. 直す候補の一覧 ----
FIX = NC[NC["分類"] == "直す候補"][["記事", "ファイル", "行番号", "観点", "該当行", "理由"]].copy()
FIX["いまのデータで結果が変わるか"] = FIX.apply(lambda r: "変わらない（同じ時刻の行が0組）" if (r["観点"] == "C07" and r["記事"].startswith("F247")) else
                                    "確かめていない" if r["観点"] == "C07" else "変わらない（書き方だけ）", axis=1)
FIX.to_csv(RES / "fix_candidates.csv", index=False)

# ---- 4. 系列ごと ----
S = F.groupby("系列").agg(記事=("記事", "nunique"), ファイル=("ファイル", "size"), 文=("文", "sum"), 行=("行", "sum")).reset_index()
S = S.merge(H.groupby("系列").size().rename("引っかかった数").reset_index(), on="系列")
S = S.merge(H[H["観点"] != "C06"].groupby("系列").size().rename("割り算のほか").reset_index(), on="系列")
S["文100個あたり"] = (100 * S["引っかかった数"] / S["文"]).round(1); S["文100個あたり（割り算のほか）"] = (100 * S["割り算のほか"] / S["文"]).round(1)
S.to_csv(RES / "by_series.csv", index=False)
per_file = H.groupby(["記事", "ファイル"]).size(); n_file_hit = len(per_file)

main = {"SQL のファイル": int(len(F)), "記事の数": int(F["記事"].nunique()), "文の数": int(F["文"].sum()), "行の数": int(F["行"].sum()),
        "引っかかった数": int(len(H)), "1件以上引っかかったファイル": int(n_file_hit), "引っかからなかった観点": T[T["引っかかった数"] == 0]["名前"].tolist(),
        "観点ごと": T.set_index("観点")[["名前", "引っかかった数", "ファイルの数", "記事の数"] + ORDER].to_dict("index"),
        "割り算のほかの94件を読んだ分類" if len(NC) == 94 else f"割り算のほかの{len(NC)}件を読んだ分類": {o: int((NC["分類"] == o).sum()) for o in ORDER},
        "割り算": {"数": int(len(D)), "守りなし": int((D["守り"] == "守りなし").sum()), "守りあり": int((D["守り"] == "守りあり").sum()),
                "[bad] の例の中": bad6, "分母の形": D6["計"].to_dict()},
        "直す候補": {"数": int(len(FIX)), "いまのデータで結果が変わる": 0, "確かめていない": int((FIX["いまのデータで結果が変わるか"] == "確かめていない").sum()),
                  "観点ごと": FIX["観点"].value_counts().to_dict()},
        "系列ごと": S.set_index("系列").to_dict("index")}
json.dump(main, open(RES / "a406_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図 ----
SRC = "このシリーズの GitHub（japan-open-data-notes）にある SQL ファイル148本をもとに作成者が集計"
COL = {"わざと書いた悪い例": GRAY, "誤検出": LIGHT, "問題なし": BLUE, "直す候補": ORANGE}
fig, ax = plt.subplots(figsize=(9, 4.8))
t = T[::-1].reset_index(drop=True); left = np.zeros(len(t))
for o in ORDER:
    ax.barh(range(len(t)), t[o], left=left, color=COL[o], label=o); left += t[o].to_numpy()
c6 = t.index[t["観点"] == "C06"][0]
ax.barh(c6, t.loc[c6, "引っかかった数"], color="#d9d8d2", label="割り算（1件ずつは読んでいない）")
for i, v in enumerate(t["引っかかった数"]): ax.text(v + 2, i, f"{v}", va="center", fontsize=9.5)
ax.set_yticks(range(len(t))); ax.set_yticklabels([f"{n}" for n in t["名前"]], fontsize=9); ax.set_xlabel("引っかかった数（SQL ファイル148本・477文）")
ax.legend(frameon=False, fontsize=8.5, loc="lower right"); ax.set_title("10個の観点を機械で当てて、引っかかった数")
save(fig, "a406_hits_by_check.png", SRC)

fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0))
ax = axes[0]; v = [int((NC["分類"] == o).sum()) for o in ORDER]
ax.bar(range(4), v, color=[COL[o] for o in ORDER])
for i, x in enumerate(v): ax.text(i, x + 0.8, f"{x}件\n({100 * x / len(NC):.0f}%)", ha="center", fontsize=9)
ax.set_xticks(range(4)); ax.set_xticklabels(["わざと書いた\n悪い例", "誤検出", "問題なし", "直す候補"], fontsize=9); ax.set_ylim(0, max(v) * 1.25)
ax.set_ylabel("件"); ax.set_title(f"割り算のほかの{len(NC)}件を、1件ずつ読んだ分類", fontsize=11)
ax = axes[1]; d = D6[::-1]
ax.barh(range(len(d)), d["守りなし"], color=ORANGE, label="守りなし"); ax.barh(range(len(d)), d["守りあり"], left=d["守りなし"], color=BLUE, label="同じ文に守りあり")
for i, (a, b) in enumerate(zip(d["守りなし"], d["守りあり"])): ax.text(a + b + 1, i, f"{a + b}", va="center", fontsize=9)
ax.set_yticks(range(len(d))); ax.set_yticklabels(d.index, fontsize=9); ax.set_xlabel("件"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"割り算{len(D)}件の、分母の形（機械の判定）", fontsize=11)
save(fig, "a406_read_labels_and_division.png", SRC, y=-0.03)

fig, ax = plt.subplots(figsize=(11, 0.9 + 0.36 * (len(FIX) + 1))); ax.axis("off")
tab = FIX.copy(); tab["場所"] = tab["記事"].str.split("_").str[0] + " " + tab["ファイル"].str.split("/").str[-1] + ":" + tab["行番号"].astype(str)
tab["観点"] = tab["観点"].map(names)
cells = tab[["観点", "場所", "いまのデータで結果が変わるか"]].values.tolist()
tb = ax.table(cellText=cells, colLabels=["観点", "場所（記事 ファイル:行）", "いまのデータで結果が変わるか"], loc="center", cellLoc="left", colWidths=[0.27, 0.40, 0.33])
tb.auto_set_font_size(False); tb.set_fontsize(8.5); tb.scale(1, 1.45)
for (r, c), cell in tb.get_celld().items():
    cell.set_edgecolor("#d9d8d2")
    if r == 0: cell.set_facecolor("#f0efec"); cell.set_text_props(weight="bold")
ax.set_title(f"読んで「直す候補」とした{len(FIX)}件", fontsize=11)
save(fig, "a406_fix_candidates.png", SRC, y=0.06)
print(json.dumps(main, ensure_ascii=False, indent=1)); print(D6); print(S.to_string())
