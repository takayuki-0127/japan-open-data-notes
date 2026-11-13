"""585 個・箱・ケースの単位が混ざった出荷明細を換算せずに足すと、品目別の数量はどれだけずれるのか。
入数マスタの漏れと、入数の変更（有効期間なし）も確かめる。架空の出荷明細と入数マスタ（seed 585）"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import DATA, SQL, RES, save, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "出典：架空の出荷明細と入数マスタ（作成者が乱数で作成、seed 585）"
rng = np.random.default_rng(585)

# ---- 1. 品目と入数 ----
NI = 300
items = pd.DataFrame({"item": [f"I{i + 1:03d}" for i in range(NI)]})
items["per_box"] = rng.choice([6, 10, 12, 20, 24], NI)
items["box_per_case"] = rng.choice([4, 6, 8, 10, 12], NI)
items["pop"] = rng.lognormal(0, 1.0, NI)               # 品目の売れやすさ
# 品目ごとに、どの単位で出やすいか（小売向けは個、卸向けは箱・ケース）
mix = rng.dirichlet([3, 2, 1], NI)
# 入数の変更：8品目は 2025-07-01 から箱の入数が 12 → 10 に変わった（それまでは12）
chg = rng.choice(items.index[items.per_box == 10], 8, replace=False)
items["per_box_before_jul"] = items["per_box"]
items.loc[chg, "per_box_before_jul"] = 12

# ---- 2. 出荷明細（2025年の1年分） ----
days = pd.date_range("2025-01-01", "2025-12-31", freq="D")
n_lines = 80_000
it = rng.choice(NI, n_lines, p=items["pop"] / items["pop"].sum())
unit = np.array([rng.choice(["個", "箱", "ケース"], p=mix[i]) for i in it])
qty = np.where(unit == "個", rng.integers(1, 25, n_lines), np.where(unit == "箱", rng.integers(1, 9, n_lines), rng.integers(1, 4, n_lines)))
d = rng.choice(days, n_lines)
lines = pd.DataFrame({"line_id": np.arange(1, n_lines + 1), "shipped_on": pd.to_datetime(d), "item": items.item.values[it], "unit": unit, "qty": qty})
lines = lines.sort_values(["shipped_on", "line_id"]).reset_index(drop=True)
lines["line_id"] = np.arange(1, len(lines) + 1)

# 本当の個数（出荷した日の入数で換算）
im = items.set_index("item")
pb = np.where(lines["shipped_on"] < "2025-07-01", im.loc[lines.item, "per_box_before_jul"].values, im.loc[lines.item, "per_box"].values)
bpc = im.loc[lines.item, "box_per_case"].values
lines["true_pcs"] = np.where(lines.unit == "個", lines.qty, np.where(lines.unit == "箱", lines.qty * pb, lines.qty * pb * bpc))

# ---- 3. 入数マスタ（今の値だけ。12品目はケースの行が漏れている） ----
miss_case = rng.choice(items.index[~items.index.isin(chg)], 12, replace=False)
mrows = []
for i, r in items.iterrows():
    mrows.append((r["item"], "個", 1))
    mrows.append((r["item"], "箱", int(r.per_box)))
    if i not in miss_case:
        mrows.append((r["item"], "ケース", int(r.per_box * r.box_per_case)))
master = pd.DataFrame(mrows, columns=["item", "unit", "pcs_per_unit"])
lines[["line_id", "shipped_on", "item", "unit", "qty"]].to_csv(DATA / "shipments.csv", index=False, date_format="%Y-%m-%d")
master.to_csv(DATA / "unit_master.csv", index=False)
hist = items.loc[chg, ["item"]].assign(valid_from="2025-01-01", valid_to="2025-06-30", pcs_per_box=12)
hist = pd.concat([hist, items.loc[chg, ["item"]].assign(valid_from="2025-07-01", valid_to="9999-12-31", pcs_per_box=10)])
hist.to_csv(DATA / "box_size_history.csv", index=False)

# ---- 4. 集計の4通り ----
x = lines.merge(master, on=["item", "unit"], how="left")
x["pcs_master"] = x["qty"] * x["pcs_per_unit"]
# 履歴を使った換算（8品目の箱・ケースは出荷日の入数で）
x["pcs_hist"] = x["pcs_master"]
mask = x["item"].isin(items.loc[chg, "item"]) & (x["shipped_on"] < "2025-07-01") & x["unit"].isin(["箱", "ケース"])
x.loc[mask, "pcs_hist"] = x.loc[mask, "pcs_master"] * 12 / 10
agg = x.groupby("item").agg(true=("true_pcs", "sum"), raw=("qty", "sum"), master=("pcs_master", "sum"), master_fill0=("pcs_master", lambda s: s.fillna(0).sum()), with_history=("pcs_hist", lambda s: s.fillna(0).sum()))
agg["err_raw"] = (agg.raw / agg.true - 1) * 100
agg["err_master"] = (agg.master_fill0 / agg.true - 1) * 100
agg["err_hist"] = (agg["with_history"] / agg["true"] - 1) * 100
agg.to_csv(RES / "per_item.csv", float_format="%.3f")

unmatched = x[x.pcs_per_unit.isna()]
top = lambda col: set(agg[col].nlargest(20).index)
r_true = agg["true"].rank(ascending=False); r_raw = agg["raw"].rank(ascending=False)
res = {"n_items": NI, "n_lines": int(len(lines)),
       "unit_share_lines_pct": (lines.unit.value_counts(normalize=True) * 100).round(1).to_dict(),
       "total_true_pcs": int(agg.true.sum()), "total_raw": int(agg.raw.sum()),
       "total_raw_ratio_pct": round(float(agg.raw.sum() / agg.true.sum() * 100), 1),
       "raw_item_err": {"median": round(float(agg.err_raw.median()), 1), "min": round(float(agg.err_raw.min()), 1), "max": round(float(agg.err_raw.max()), 1),
                         "n_items_abs_over_50": int((agg.err_raw.abs() > 50).sum())},
       "raw_top20_overlap": len(top("true") & top("raw")),
       "raw_rank_spearman": round(float(agg.true.corr(agg.raw, method="spearman")), 3),
       "raw_rank_moved_50plus": int(((r_true - r_raw).abs() >= 50).sum()),
       "master_missing_items": int(len(miss_case)), "unmatched_lines": int(len(unmatched)),
       "unmatched_true_pcs": int(unmatched.true_pcs.sum()),
       "master_missing_item_err": {"median": round(float(agg.loc[items.item[miss_case], "err_master"].median()), 1),
                                    "min": round(float(agg.loc[items.item[miss_case], "err_master"].min()), 1),
                                    "max": round(float(agg.loc[items.item[miss_case], "err_master"].max()), 1)},
       "inner_join_drops_pcs_pct": round(float(unmatched.true_pcs.sum() / agg.true.sum() * 100), 2),
       "pack_change_items": int(len(chg)),
       "pack_change_err_master": {"median": round(float(agg.loc[items.item[chg], "err_master"].median()), 1),
                                  "min": round(float(agg.loc[items.item[chg], "err_master"].min()), 1),
                                  "max": round(float(agg.loc[items.item[chg], "err_master"].max()), 1)},
       "hist_err_max_abs_excluding_missing": round(float(agg.drop(index=items.item[miss_case]).err_hist.abs().max()), 6)}

# ---- 5. SQL（DuckDB、1スレッド）：マスタで換算し、換算できない明細を数える ----
con = duckdb.connect(); con.execute("SET threads=1")
for t in ["shipments", "unit_master"]:
    con.execute(f"CREATE TABLE {t} AS SELECT * FROM read_csv_auto('{DATA / (t + '.csv')}')")
sq = con.execute((SQL / "02_convert_duckdb.sql").read_text()).df().set_index("item")
sq.to_csv(RES / "sql_per_item.csv")
res["sql_match_python"] = bool((sq.reindex(agg.index)["pcs_converted"].fillna(0).astype(int).values == agg.master_fill0.astype(int).values).all()
                               and int(sq["unmatched_lines"].sum()) == len(unmatched)
                               and (sq.reindex(agg.index)["qty_raw"].astype(int).values == agg.raw.astype(int).values).all())
json.dump(res, open(RES / "a585_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))

# ---- 6. 図 ----
fig, ax = plt.subplots(figsize=(8, 4.2))
ax.hist(agg.raw / agg.true * 100, bins=np.arange(0, 84, 3), color=BLUE, edgecolor="white")
ax.axvline(res["total_raw_ratio_pct"], color=ORANGE, lw=1.5, ls="--")
ax.text(res["total_raw_ratio_pct"] + 0.5, ax.get_ylim()[1] * 0.9, f"全体では{res['total_raw_ratio_pct']:.1f}%", color=ORANGE, fontsize=10)
ax.set_xlabel("換算せずに足した数量 ÷ 本当の個数（%）"); ax.set_ylabel("品目数（300品目）")
ax.set_title("単位をそろえずに足すと、品目別の数量は本当の何%になるか")
save(fig, "a585_raw_ratio.png", SRC)

fig, ax = plt.subplots(figsize=(6.5, 5.5))
ax.scatter(agg.true, agg.raw, s=14, color=BLUE, alpha=0.7)
lim = [agg.true.min() * 0.8, agg.true.max() * 1.2]
ax.plot(lim, lim, color=GRAY, lw=0.8, ls="--")
ax.set_xscale("log"); ax.set_yscale("log")
ax.set_xlabel("本当の個数（対数目盛。点線は同じ値）"); ax.set_ylabel("換算せずに足した数量（対数目盛）")
ax.set_title(f"品目の並びも変わる（順位相関 {res['raw_rank_spearman']:.2f}、上位20の重なり {res['raw_top20_overlap']}品目）", fontsize=11)
save(fig, "a585_scatter.png", SRC)

lab = [f"ケースの行が\nない12品目", "入数が7月に変わった\n8品目（マスタは今の値）"]
d1 = agg.loc[items.item[miss_case], "err_master"]; d2 = agg.loc[items.item[chg], "err_master"]
fig, ax = plt.subplots(figsize=(8, 4.2))
for j, dd in enumerate([d1, d2]):
    ax.scatter(np.full(len(dd), j) + rng.uniform(-0.12, 0.12, len(dd)), dd, color=[ORANGE, GREEN][j], s=30)
    ax.text(j + 0.2, dd.median(), f"中央値 {dd.median():.1f}%", va="center", fontsize=9)
ax.axhline(0, color=INK, lw=0.8)
ax.set_xticks([0, 1]); ax.set_xticklabels(lab); ax.set_xlim(-0.5, 1.8)
ax.set_ylabel("マスタで換算した個数の、本当の個数とのずれ（%）")
ax.set_title("入数マスタで換算しても、マスタの漏れと入数の変更で数量はずれる")
save(fig, "a585_master_issues.png", SRC)
