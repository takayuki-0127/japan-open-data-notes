"""775 前回の順位と比べるとき、前回いなかった店を外すかどうかで、「順位が上がった店」の数はどれだけ変わるのか

架空の店の2期分の売上。前期は100店。今期は、前期の店のうち10店が閉まり、新しい店が15店加わる（新しい店は売上が大きめ）。
今期の店ごとに「順位が上がった」かを3通りで数える：
 A 各期の全店の順位をそのまま比べる（前回いなかった店は比べない）
 B 前回いなかった店を「前回は最下位の次」として比べる
 C 両方の期にいた店だけで順位を付け直して比べる（順位を詰める）
新店の数を0〜30に変えた場合も数える。DuckDB（1スレッド）と pandas で一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN

SRC = "出典：架空の店の2期分の売上（作成者が乱数で作成、seed 775）"
rng = np.random.default_rng(775)
QTXT = "\n".join(l for l in (SQL / "02_rank_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")


def make(n_new, n_close=10, n_prev=100):
    s1 = np.round(rng.lognormal(10, .5, n_prev)).astype(int) * 1000
    keep = np.sort(rng.choice(n_prev, n_prev - n_close, replace=False))
    s2 = np.round(s1[keep] * rng.lognormal(0, .15, len(keep))).astype(int)
    new = np.round(rng.lognormal(10.4, .4, n_new)).astype(int) * 1000
    p1 = pd.DataFrame({"period": 1, "store_id": np.arange(1, n_prev + 1), "sales": s1})
    p2 = pd.DataFrame({"period": 2, "store_id": np.r_[keep + 1, np.arange(n_prev + 1, n_prev + 1 + n_new)], "sales": np.r_[s2, new]})
    return pd.concat([p1, p2], ignore_index=True)


def count(df, check=False):
    con = duckdb.connect(); con.execute("SET threads=1"); con.register("sales", df)
    Q = con.execute(QTXT).df()
    if check:   # pandas でも同じ順位になるか
        r = df.copy(); r["rk"] = r.groupby("period").sales.rank(method="min", ascending=False).astype(int)
        c = r[r.period == 2].set_index("store_id"); p = r[r.period == 1].set_index("store_id")
        assert (Q.set_index("store_id").rank_now == c.rk.sort_index()).all()
        assert (Q.set_index("store_id").rank_prev.dropna() == p.rk.reindex(Q.dropna(subset=["rank_prev"]).store_id).values).all()
    common = Q.rank_prev.notna()
    A = int((Q.rank_now[common] < Q.rank_prev[common]).sum())
    B = int((Q.rank_now < Q.rank_prev_bottom).sum())
    C = int((Q.rank_now_common[common] < Q.rank_prev_common[common]).sum())
    Adown = int((Q.rank_now[common] > Q.rank_prev[common]).sum())
    Cdown = int((Q.rank_now_common[common] > Q.rank_prev_common[common]).sum())
    return Q, dict(up_A=A, up_B=B, up_C=C, down_A=Adown, down_C=Cdown, common=int(common.sum()), new=int((~common).sum()),
                   mean_change_A=float((Q.rank_prev - Q.rank_now)[common].mean()), mean_change_C=float((Q.rank_prev_common - Q.rank_now_common)[common].mean()))


df = make(15)
DATA.mkdir(exist_ok=True); df.to_csv(DATA / "sales.csv", index=False)
Q, main = count(df, check=True)
Q.to_csv(RES / "ranks.csv", index=False)
rows = []
for k in [0, 5, 10, 15, 20, 30]:
    for r in range(30):
        _, d = count(make(k)); d.update(n_new=k, rep=r); rows.append(d)
V = pd.DataFrame(rows).groupby("n_new").mean().drop(columns="rep").reset_index()
V.to_csv(RES / "by_new_stores.csv", index=False)
out = {"prev_stores": 100, "closed": 10, "new": 15, "now_stores": len(Q), **main,
       "by_new": {int(r.n_new): {k: round(getattr(r, k), 2) for k in ["up_A", "up_B", "up_C", "down_A", "down_C"]} for r in V.itertuples()},
       "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a775_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：3通りの「上がった店」
fig, ax = plt.subplots(figsize=(9, 4.6))
lab = ["A 全店の順位を\nそのまま比べる", "B 新店を「前回は\n最下位の次」とする", "C 両方にいた店だけで\n順位を詰める"]
vals = [main["up_A"], main["up_B"], main["up_C"]]
b = ax.bar(lab, vals, color=[ORANGE, GREEN, BLUE])
for bb, v in zip(b, vals): ax.text(bb.get_x() + bb.get_width() / 2, v + .8, f"{v}店", ha="center")
ax.set_ylabel(f"「順位が上がった」店の数（今期{len(Q)}店のうち）")
ax.set_title("同じ2期の売上でも、数え方で「上がった店」は大きく変わる")
save(fig, "a775_three.png", SRC)
# 図2：新店の数を変える
fig, ax = plt.subplots(figsize=(9, 4.6))
ax.plot(V.n_new, V.up_A, "o-", color=ORANGE, label="A 全店の順位をそのまま")
ax.plot(V.n_new, V.up_B, "s-", color=GREEN, label="B 新店は前回最下位の次")
ax.plot(V.n_new, V.up_C, "^-", color=BLUE, label="C 両方にいた店だけ")
ax.set_xlabel("今期に加わった新店の数（前期100店、10店が閉店）"); ax.set_ylabel("「上がった」店の数（30回の平均）")
ax.legend(frameon=False); ax.set_title("閉店だけなら A は「上がった」が多く、新店が増えると減る。C はいつも約41店")
save(fig, "a775_by_new.png", SRC)
# 図3：前回と今回の順位（A）
fig, ax = plt.subplots(figsize=(7.5, 6))
c = Q[Q.rank_prev.notna()]
ax.scatter(c.rank_prev, c.rank_now, s=14, color=BLUE, label="両方にいた店")
ax.scatter(np.full((Q.rank_prev.isna()).sum(), 103), Q.rank_now[Q.rank_prev.isna()], s=18, color=ORANGE, marker="s", label="新店（前回なし）")
ax.plot([0, 105], [0, 105], color=GRAY, ls="--")
ax.set_xlabel("前回の順位（右端の列は前回いなかった店）"); ax.set_ylabel("今回の順位"); ax.invert_yaxis()
ax.legend(frameon=False, loc="lower right"); ax.set_title("新店が上位に入ると、既存の店は押し下げられる")
save(fig, "a775_scatter.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
