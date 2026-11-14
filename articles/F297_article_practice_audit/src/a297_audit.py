"""F297 自分の記事1,066本の決まりの守り方を数える。data/ の CSV だけで動く（乱数は並べ替えの区間にだけ使う、seed 297）。
使い方: cd src && python a297_audit.py
"""
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Noto Sans CJK JP"
HERE = Path(__file__).resolve().parents[1]
D, R, FG = HERE / "data", HERE / "results", HERE / "figures"
R.mkdir(exist_ok=True); FG.mkdir(exist_ok=True)
rng = np.random.default_rng(297)

a = pd.read_csv(D / "articles.csv")
a["group"] = np.where(a.kind == "看板", "看板（F）", (a.no // 100 * 100).map(lambda x: f"{x:03d}〜{x + 99:03d}"))
a.loc[(a.kind == "一覧") & (a.no >= 800), "group"] = "700〜799"   # 800番は1本だけなので 700番台に含める
order = sorted(g for g in a.group.unique() if g[0].isdigit()) + ["看板（F）"]

# A. 決まりの守り方（区分ごとの割合）
cols = {"has_cannot": "「言えないこと」の節", "has_robust": "「頑健性」の節", "has_checked": "「確かめたこと／再現」の節",
        "has_plan": "事前の計画", "fictional": "架空のデータ", "simulation": "シミュレーション"}
A = a.groupby("group")[list(cols)].mean().reindex(order).rename(columns=cols)
A.insert(0, "本数", a.groupby("group").size().reindex(order))
A["推測（1本あたり）"] = a.groupby("group").guess_count.mean().reindex(order)
A["README の長さ（中央値・字）"] = a.groupby("group").readme_chars.median().reindex(order)
A.round(3).to_csv(R / "A_practice_by_group.csv", encoding="utf-8")

# 「言えないこと」が付き始めた番号：一覧の記事で、それ以降の割合が 95% を超える最初の番号
L = a[a.kind == "一覧"].sort_values("no")
rev = L.has_cannot[::-1].expanding().mean()[::-1].values
start_no = int(L.no.values[np.argmax(rev >= 0.95)])

# B. 設計の変更（668〜800）の中身
dc = pd.read_csv(D / "design_changes.csv", dtype=str)
# 変えたことの区分は、CORRECTIONS.md の文を読んで手で付けた（data/design_changes_labels.csv）
lab = pd.read_csv(D / "design_changes_labels.csv", dtype=str)
dc = dc.merge(lab, on="no", how="left")
assert dc.kind.notna().all(), "区分の付いていない行がある"
in_range = a[(a.kind == "一覧") & (a.no >= 668) & (a.no <= 800)]
B = dc.kind.value_counts().rename_axis("変えたこと").reset_index(name="本数")
B["668〜800 の本数に対する割合"] = (B["本数"] / len(in_range)).round(3)
B.to_csv(R / "B_design_changes.csv", index=False, encoding="utf-8")
dc.to_csv(R / "B_design_changes_labeled.csv", index=False, encoding="utf-8")

# C. 確かめていないこと・流し直し
un = pd.read_csv(D / "unverified.csv", dtype=str)
sql_arts = a[(a.kind == "一覧") & (a.has_sql == 1)]
rep = json.load(open(D / "repro_sample.json", encoding="utf-8"))
rr = pd.DataFrame(rep["results"])
ok = int((rr.status == "一致").sum()); n = len(rr)
# 一致の割合の区間（Clopper–Pearson）
from scipy.stats import beta
lo = beta.ppf(0.025, ok, n - ok + 1) if ok > 0 else 0.0
hi = beta.ppf(0.975, ok + 1, n - ok) if ok < n else 1.0
C = {"unverified_tsql": int((un.kind == "T-SQL").sum()), "unverified_excel": int((un.kind == "Excel").sum()),
     "sql_articles_in_list": int(len(sql_arts)),
     "repro_n": n, "repro_identical": ok, "repro_ci95": [round(float(lo), 3), round(float(hi), 3)],
     "repro_population": rep["population"], "repro_seed": rep["seed"],
     "repro_median_sec": float(rr.sec.median()), "repro_max_sec": float(rr.sec.max())}

main = {"n_articles": int(len(a)), "n_list": int((a.kind == "一覧").sum()), "n_flagship": int((a.kind == "看板").sum()),
        "cannot_start_no": start_no,
        "cannot_share_before": round(float(L[L.no < start_no].has_cannot.mean()), 3),
        "cannot_share_after": round(float(L[L.no >= start_no].has_cannot.mean()), 3),
        "fictional_share_list_300plus": round(float(L[L.no >= 300].fictional.mean()), 3),
        "fictional_share_flagship": round(float(a[a.kind == "看板"].fictional.mean()), 3),
        "robust_share_flagship": round(float(a[a.kind == "看板"].has_robust.mean()), 3),
        "robust_share_list": round(float(L.has_robust.mean()), 3),
        "plan_share_flagship": round(float(a[a.kind == "看板"].has_plan.mean()), 3),
        "plan_share_list": round(float(L.has_plan.mean()), 3),
        "design_changes": int(len(dc)), "design_change_share_668_800": round(len(dc) / len(in_range), 3),
        "n_668_800": int(len(in_range)), **C}
json.dump(main, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# 図1：決まりの守り方（区分ごと）
fig, ax = plt.subplots(figsize=(10, 5.2), dpi=120)
x = np.arange(len(order)).astype(float); x[-1] += 0.6   # 看板は番号の並びではないので、離して点だけ置く
for c, col, mk in (("「言えないこと」の節", "#1f5f8b", "o"), ("「頑健性」の節", "#c0692b", "s"),
                   ("事前の計画", "#6b4c9a", "^"), ("架空のデータ", "#2e7d4f", "D")):
    ax.plot(x[:-1], A[c].values[:-1] * 100, marker=mk, color=col, label=c, lw=2)
    ax.plot(x[-1:], A[c].values[-1:] * 100, marker=mk, color=col, ls="none", ms=8)
ax.axvline(x[-1] - 0.8, color="#bbb", lw=1)
ax.set_xticks(x, [f"{g}\n({k}本)" for g, k in zip(order, A["本数"])], fontsize=9)
ax.set_ylabel("その区分の記事のうち、当てはまる割合（%）"); ax.set_ylim(-3, 103)
ax.set_title(f"「言えないこと」は {start_no} 番から付けるようになり、短い記事は架空のデータへ移った")
ax.legend(fontsize=9, loc="center left"); ax.grid(axis="y", alpha=.3)
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(FG / "f297_01_practice.png"); plt.close(fig)

# 図2：設計の変更の中身
fig, ax = plt.subplots(figsize=(9, 3.8), dpi=120)
B2 = B.sort_values("本数")
ax.barh(B2["変えたこと"], B2["本数"], color="#1f5f8b")
for y_, v in enumerate(B2["本数"]): ax.text(v + .2, y_, f"{v}本", va="center")
ax.set_xlabel(f"本数（668〜800 の {len(in_range)} 本のうち {len(dc)} 本で、作る途中に何かを変えた）")
ax.set_title("作る途中で変えたことの内訳")
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(FG / "f297_02_changes.png"); plt.close(fig)

# 図3：確かめた範囲（流し直し・T-SQL）
fig, axs = plt.subplots(1, 2, figsize=(10, 4), dpi=120)
axs[0].bar(["一致", "不一致・失敗"], [ok, n - ok], color=["#2e7d4f", "#b5452b"])
axs[0].set_title(f"無作為に選んだ {n} 本を空のフォルダで流し直す\n一致 {ok}/{n}（95%区間 {lo:.0%}〜{hi:.0%}）", fontsize=10)
axs[1].bar(["SQL を含む一覧の記事", "T-SQL 版を\nSQL Server で未実行"], [len(sql_arts), C["unverified_tsql"]], color=["#1f5f8b", "#c0692b"])
axs[1].set_title("SQL Server では動かしていない書き方が残る", fontsize=10)
for ax in axs:
    for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(FG / "f297_03_verified.png"); plt.close(fig)
print(json.dumps(main, ensure_ascii=False, indent=1))
