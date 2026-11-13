"""582 複数の担当者で受けた案件の成果を、主担当に全部付けるか、人数で割るか、関与度の比で分けるかで、
担当者別の実績と順位はどれだけ入れ替わるのか。架空の案件と担当者（seed 582）"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "出典：架空の案件と担当者（作成者が乱数で作成、seed 582）"
rng = np.random.default_rng(582)

# ---- 1. 架空の担当者と案件 ----
# 営業20人（主担当になりやすい）と、専門担当10人（応援に入りやすい）
people = pd.DataFrame({"person_id": [f"S{i:02d}" for i in range(1, 21)] + [f"T{i:02d}" for i in range(1, 11)],
                       "group": ["営業"] * 20 + ["専門"] * 10})
w_main = np.r_[rng.lognormal(0, 0.45, 20), rng.lognormal(-1.6, 0.45, 10)]
w_sup = np.r_[rng.lognormal(-0.7, 0.45, 20), rng.lognormal(0.6, 0.45, 10)]
N_DEAL = 1200
team_size_p = [0.45, 0.30, 0.17, 0.08]


def make_deals(p_team, seed):
    r = np.random.default_rng(seed)
    deals, roles = [], []
    for d in range(1, N_DEAL + 1):
        k = r.choice([1, 2, 3, 4], p=p_team)
        main = r.choice(30, p=w_main / w_main.sum())
        ws = w_sup.copy(); ws[main] = 0
        sup = r.choice(30, size=k - 1, replace=False, p=ws / ws.sum()) if k > 1 else np.array([], int)
        # 大きい案件ほど人が多い
        amount = int(round(r.lognormal(np.log(800_000) + 0.35 * (k - 1), 0.7), -3))
        # 関与度（記録した工数の比）：主担当は多め
        raw = np.r_[r.gamma(4.0), r.gamma(2.0, size=k - 1)] if k > 1 else np.array([1.0])
        share = raw / raw.sum()
        deals.append((f"D{d:04d}", amount, k))
        for j, (pid, sh) in enumerate(zip(np.r_[main, sup], share)):
            roles.append((f"D{d:04d}", people.person_id[pid], "主" if j == 0 else "応援", round(float(sh), 4)))
    dl = pd.DataFrame(deals, columns=["deal_id", "amount", "team_size"])
    rl = pd.DataFrame(roles, columns=["deal_id", "person_id", "role", "involvement"])
    # 小数を丸めたので、案件ごとに合計1へ直す（最後の人で調整）
    fix = rl.groupby("deal_id")["involvement"].transform("sum")
    rl["involvement"] = (rl["involvement"] / fix).round(4)
    return dl, rl


deals, roles = make_deals(team_size_p, 582)
deals.to_csv(DATA / "deals.csv", index=False)
roles.to_csv(DATA / "deal_members.csv", index=False)


def credit(deals, roles):
    x = roles.merge(deals, on="deal_id")
    out = pd.DataFrame(index=people.person_id)
    out["main_only"] = x[x.role == "主"].groupby("person_id")["amount"].sum()
    out["equal"] = (x["amount"] / x["team_size"]).groupby(x["person_id"]).sum()
    out["involvement"] = (x["amount"] * x["involvement"]).groupby(x["person_id"]).sum()
    out["full_each"] = x.groupby("person_id")["amount"].sum()
    out = out.fillna(0)
    out["n_deals"] = x.groupby("person_id").size().reindex(out.index).fillna(0).astype(int)
    out["n_main"] = x[x.role == "主"].groupby("person_id").size().reindex(out.index).fillna(0).astype(int)
    return out


c = credit(deals, roles)
c["group"] = people.set_index("person_id")["group"]
METH = {"main_only": "主担当に全額", "equal": "人数で均等割り", "involvement": "関与度の比"}
for k in list(METH) + ["full_each"]:
    c["rank_" + k] = c[k].rank(ascending=False, method="min").astype(int)
c.to_csv(RES / "person_credit.csv", float_format="%.0f")

total = int(deals["amount"].sum())


def rank_stats(c):
    s = {}
    for a, b in [("main_only", "equal"), ("main_only", "involvement"), ("equal", "involvement")]:
        d = (c["rank_" + a] - c["rank_" + b]).abs()
        top_a = set(c.nsmallest(5, a and "rank_" + a).index); top_b = set(c.nsmallest(5, "rank_" + b).index)
        s[f"{a}_vs_{b}"] = {"n_rank_changed": int((d > 0).sum()), "n_rank_moved_5plus": int((d >= 5).sum()),
                            "max_move": int(d.max()), "spearman": round(float(c[a].corr(c[b], method="spearman")), 3),
                            "top5_overlap": len(top_a & top_b)}
    return s


rs = rank_stats(c)
grp = c.groupby("group")[["main_only", "equal", "involvement", "full_each"]].sum()
grp_share = (grp / total * 100).round(2)
mover = (c["rank_main_only"] - c["rank_involvement"]).idxmax()

# ---- 2. 複数人の案件が増えると、入れ替わりはどう増えるか ----
sweep = []
for p1 in [0.8, 0.6, 0.45, 0.3, 0.15]:
    rest = 1 - p1
    pt = [p1, rest * 0.55, rest * 0.30, rest * 0.15]
    for rep in range(20):
        dl, rl = make_deals(pt, 10_000 + int(p1 * 100) * 100 + rep)
        cc = credit(dl, rl)
        d = (cc["main_only"].rank(ascending=False) - cc["involvement"].rank(ascending=False)).abs()
        sweep.append({"share_multi": round(1 - p1, 2), "rep": rep, "mean_abs_move": float(d.mean()),
                      "spearman": float(cc["main_only"].corr(cc["involvement"], method="spearman"))})
sw = pd.DataFrame(sweep)
sws = sw.groupby("share_multi").agg(mean_abs_move=("mean_abs_move", "mean"), spearman=("spearman", "mean")).round(3)
sws.to_csv(RES / "sweep_multi_share.csv")

# ---- 3. SQL（DuckDB、1スレッド）で関与度の比の集計を突き合わせ ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute(f"CREATE TABLE deals AS SELECT * FROM read_csv_auto('{DATA / 'deals.csv'}')")
con.execute(f"CREATE TABLE deal_members AS SELECT * FROM read_csv_auto('{DATA / 'deal_members.csv'}')")
sq = con.execute((SQL / "02_credit_duckdb.sql").read_text()).df().set_index("person_id")
sq.to_csv(RES / "sql_credit.csv", float_format="%.2f")
sql_match = bool(np.allclose(sq.reindex(c.index).fillna(0)[["main_only", "equal_split", "by_involvement"]].to_numpy(),
                             c[["main_only", "equal", "involvement"]].to_numpy(), atol=0.5))

res = {"n_deals": N_DEAL, "n_people": 30, "total_amount": total,
       "share_multi_person_deals_pct": round(float((deals.team_size > 1).mean() * 100), 1),
       "share_amount_multi_person_pct": round(float(deals.loc[deals.team_size > 1, "amount"].sum() / total * 100), 1),
       "rank_stats": rs,
       "group_share_pct": grp_share.to_dict(),
       "full_each_total_ratio": round(float(c["full_each"].sum() / total), 3),
       "biggest_mover": {"person": mover, "group": c.loc[mover, "group"], "rank_main": int(c.loc[mover, "rank_main_only"]),
                         "rank_equal": int(c.loc[mover, "rank_equal"]), "rank_inv": int(c.loc[mover, "rank_involvement"]),
                         "n_deals": int(c.loc[mover, "n_deals"]), "n_main": int(c.loc[mover, "n_main"])},
       "specialists_rank_main_median": float(c[c.group == "専門"]["rank_main_only"].median()),
       "specialists_rank_inv_median": float(c[c.group == "専門"]["rank_involvement"].median()),
       "sweep": sws.reset_index().to_dict(orient="records"),
       "sql_match_python": sql_match}
json.dump(res, open(RES / "a582_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 4. 図 ----
o = c.sort_values("rank_involvement")
fig, ax = plt.subplots(figsize=(9, 5))
cols = [BLUE, ORANGE, GREEN]
for j, (k, lab) in enumerate(METH.items()):
    ax.plot(range(3), [0, 0, 0], alpha=0)
xs = np.arange(3)
for pid, r in o.iterrows():
    ys = [r["rank_main_only"], r["rank_equal"], r["rank_involvement"]]
    col = ORANGE if r["group"] == "専門" else BLUE
    ax.plot(xs, ys, "-o", color=col, alpha=0.75, ms=4, lw=1.2)
ax.set_xticks(xs); ax.set_xticklabels(list(METH.values()))
ax.set_ylim(31, 0); ax.set_yticks([1, 5, 10, 15, 20, 25, 30]); ax.set_ylabel("担当者別の実績の順位（1位が上）")
ax.plot([], [], "-o", color=BLUE, label="営業（主担当になりやすい）"); ax.plot([], [], "-o", color=ORANGE, label="専門（応援に入りやすい）")
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2, fontsize=9)
ax.set_title("同じ案件でも、成果の付け方で30人の順位はどう入れ替わるか")
save(fig, "a582_rank_slope.png", SRC)

fig, ax = plt.subplots(figsize=(8, 4))
labs = list(METH.values()) + ["全員に全額"]
v_sales = [grp_share.loc["営業", k] for k in ["main_only", "equal", "involvement", "full_each"]]
v_spec = [grp_share.loc["専門", k] for k in ["main_only", "equal", "involvement", "full_each"]]
ax.bar(labs, v_sales, color=BLUE, label="営業20人")
ax.bar(labs, v_spec, bottom=v_sales, color=ORANGE, label="専門10人")
for i, (a, b) in enumerate(zip(v_sales, v_spec)):
    ax.text(i, a + b + 3, f"計{a + b:.0f}%\nうち専門{b:.0f}%", ha="center", va="bottom", fontsize=9.5)
ax.axhline(100, color=INK, lw=0.8, ls="--")
ax.set_ylim(0, 260); ax.set_ylabel("売上合計に対する割合（%）"); ax.legend(frameon=False, loc="upper left")
ax.set_title("付け方ごとの、営業と専門の取り分（合計は100%になるか）")
save(fig, "a582_group_share.png", SRC)

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(sws.index * 100, sws["mean_abs_move"], "o-", color=BLUE)
for x_, y_ in zip(sws.index * 100, sws["mean_abs_move"]):
    ax.text(x_, y_ + 0.15, f"{y_:.1f}", ha="center", fontsize=9)
ax.set_xlabel("複数人で受けた案件の割合（%）"); ax.set_ylabel("順位の動きの平均（位）")
ax.set_title("複数人の案件が多いほど、「主担当に全額」と「関与度の比」の順位は離れる")
save(fig, "a582_sweep.png", SRC + "（割合ごとに20回の平均）")
