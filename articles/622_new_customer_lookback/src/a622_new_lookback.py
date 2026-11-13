"""622 「新規の顧客」を過去何年さかのぼって判定するかで、新規の割合はどれだけ変わるのか

架空の顧客 4万人の月ごとの購入を 2010年1月〜2025年12月で作る（初めて買う月はこの間に散らばる）。
買っている間は月ごとに買う確率（人による）で買い、毎月 3% の確率で離れる。離れた人の 35% は、6〜60か月あとに戻る。
手元のデータは 2018年1月から、とする（それより前の購入は見えない）。
2025年に買った人を「新規」と判定する4通り：前回の購入から 12・24・36か月より長くあいている／手元のデータに前回がない（全期間）。
本当の新規（2010年以降で初めての購入）と比べる。24か月の判定は SQL（DuckDB、1スレッド）でも出し、Python と一致を確かめる。
数字は置いた買い方・離れ方・戻り方で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の顧客の購買履歴（作成者が乱数で作成、seed 622）"
rng = np.random.default_rng(622)
NC = 40_000
T = 16 * 12                     # 2010-01 .. 2025-12
OFF = 8 * 12                    # 2018-01 は t=96
start = rng.integers(0, T, NC)  # 初めて買える月
p_buy = np.clip(rng.beta(1.2, 3.0, NC), 0.02, 0.95)
active = np.zeros(NC, bool); back_at = np.full(NC, -1)
rec = []
for t in range(T):
    active |= (start == t)
    ret = back_at == t
    active |= ret; back_at[ret] = -1
    buy = active & (rng.random(NC) < p_buy)
    buy |= (start == t)                      # 最初の月は必ず買う
    ids = np.nonzero(buy)[0]
    rec.append(np.column_stack([ids, np.full(len(ids), t)]))
    leave = active & (rng.random(NC) < 0.03) & (start != t)
    active &= ~leave
    comeback = leave & (rng.random(NC) < 0.35)
    back_at[comeback] = t + rng.integers(6, 61, comeback.sum())
P = pd.DataFrame(np.vstack(rec), columns=["customer_id", "t"]).sort_values(["customer_id", "t"]).reset_index(drop=True)
P["prev_t"] = P.groupby("customer_id").t.shift()
P["true_new"] = P.prev_t.isna()
# 手元のデータ（2018年以降）
V = P[P.t >= OFF].copy()
V["ym"] = V.t - OFF + 1
V["prev_ym"] = V.groupby("customer_id").ym.shift()
Y = V[V.ym >= 85].copy()          # 2025年
for k in [12, 24, 36]:
    Y[f"new_{k}"] = Y.prev_ym.isna() | (Y.ym - Y.prev_ym > k)
Y["new_all"] = Y.prev_ym.isna()
# 2025年の購入者（人単位：その年最初の購入月で判定）
first25 = Y.sort_values("ym").groupby("customer_id").head(1)
cols = ["true_new", "new_12", "new_24", "new_36", "new_all"]
year = {c: int(first25[c].sum()) for c in cols}
buyers25 = int(len(first25))
share = {c: round(100 * year[c] / buyers25, 2) for c in cols}
# 本当の新規との食い違い
conf = {}
for c in cols[1:]:
    conf[c] = {"counted": year[c], "true_new_counted": int((first25[c] & first25.true_new).sum()),
               "returners_counted_as_new": int((first25[c] & ~first25.true_new).sum()),
               "true_new_missed": int((~first25[c] & first25.true_new).sum())}
# 戻ってきた人の空白の長さ
gaps = (first25.ym - first25.prev_ym).dropna()
true_gap = (first25.t - first25.prev_t).dropna()
# 月ごと（購入月ごとに判定）
mon = Y.groupby("ym")[cols].sum().astype(int)
mon["buyers"] = Y.groupby("ym").size()
mon.index = [f"2025-{m:02d}" for m in range(1, 13)]
mon.to_csv(RES / "by_month_2025.csv")
# 判定の年ごとの推移（全期間で判定すると、データの初めの年ほど新規が多い）
yr_rows = []
for y0 in range(2018, 2026):
    lo, hi = (y0 - 2018) * 12 + 1, (y0 - 2018) * 12 + 12
    s = V[(V.ym >= lo) & (V.ym <= hi)].sort_values("ym").groupby("customer_id").head(1)
    n = len(s)
    yr_rows.append({"year": y0, "buyers": n, "true_new_pct": 100 * s.true_new.mean(),
                    "new_all_pct": 100 * s.prev_ym.isna().mean(),
                    "new_24_pct": 100 * (s.prev_ym.isna() | (s.ym - s.prev_ym > 24)).mean()})
yr = pd.DataFrame(yr_rows)
yr.round(2).to_csv(RES / "by_year_share.csv", index=False)

# SQL
con = duckdb.connect(); con.execute("SET threads=1")
con.register("buy_months", V[["customer_id", "ym"]])
q = (SQL / "02_new_customer_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
sq = con.execute(q).df()
assert (sq.new_24m.to_numpy() == mon.new_24.to_numpy()).all() and (sq.buyers.to_numpy() == mon.buyers.to_numpy()).all()
sq.to_csv(RES / "sql_new_24m_by_month.csv", index=False)

out = {"customers": NC, "data_from": "2018-01", "buyers_2025": buyers25, "new_count": year, "new_share_pct": share,
       "vs_true": conf, "gap_months_since_prev_purchase": {"median": float(gaps.median()), "p75": float(gaps.quantile(.75)), "p90": float(gaps.quantile(.9))},
       "by_year": yr.round(2).to_dict(orient="records"),
       "month_new_pct_range": {c: [round(float((mon[c] / mon.buyers).min() * 100), 2), round(float((mon[c] / mon.buyers).max() * 100), 2)] for c in cols}}
json.dump(out, open(RES / "a622_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"definition": cols, "count": [year[c] for c in cols], "share_pct": [share[c] for c in cols]}).to_csv(RES / "summary.csv", index=False)

LAB = {"true_new": "本当の新規", "new_12": "12か月あいたら新規", "new_24": "24か月", "new_36": "36か月", "new_all": "手元のデータに前回がない"}
COL = {"true_new": INK, "new_12": ORANGE, "new_24": BLUE, "new_36": LIGHT, "new_all": GREEN}
# 図1
fig, ax = plt.subplots(figsize=(8.5, 4))
ks = cols
ax.barh([LAB[c] for c in ks][::-1], [share[c] for c in ks][::-1], color=[COL[c] for c in ks][::-1])
for i, c in enumerate(ks[::-1]):
    ax.text(share[c], i, f" {share[c]:.1f}%（{year[c]:,}人）", va="center", fontsize=9)
ax.set_xlim(0, max(share.values()) * 1.45); ax.set_xlabel("2025年に買った人のうち「新規」の割合（%）")
ax.set_title(f"判定のしかたで、新規の割合はこれだけ変わる（2025年に買った {buyers25:,}人）")
save(fig, "a622_share_by_definition.png", SRC)

# 図2：内訳
fig, ax = plt.subplots(figsize=(8.5, 4))
ds = cols[1:]
a = [conf[c]["true_new_counted"] for c in ds]; b = [conf[c]["returners_counted_as_new"] for c in ds]; m = [conf[c]["true_new_missed"] for c in ds]
y = np.arange(len(ds))[::-1]
ax.barh(y, a, color=BLUE, label="本当の新規")
ax.barh(y, b, left=a, color=ORANGE, label="戻ってきた人を新規と数えた")
ax.set_yticks(y); ax.set_yticklabels([LAB[c] for c in ds])
for yy, aa, bb in zip(y, a, b):
    ax.text(aa + bb, yy, f" 戻り {bb:,}人", va="center", fontsize=9)
ax.set_xlabel("人数"); ax.legend(frameon=False, fontsize=9, loc="lower right"); ax.set_xlim(right=(max(a) + max(b)) * 1.3)
ax.set_title("「新規」の中身：戻ってきた人がどれだけ混ざるか")
save(fig, "a622_breakdown.png", SRC)

# 図3：年ごと
fig, ax = plt.subplots(figsize=(8.5, 4))
ax.plot(yr.year, yr.true_new_pct, marker="o", color=INK, label="本当の新規")
ax.plot(yr.year, yr.new_all_pct, marker="s", color=GREEN, label="手元のデータに前回がない")
ax.plot(yr.year, yr.new_24_pct, marker="^", color=BLUE, label="24か月あいたら新規")
ax.set_ylabel("その年に買った人のうち新規の割合（%）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("データの始まり（2018年）に近い年ほど、全期間の判定は新規を多く数える")
save(fig, "a622_by_year.png", SRC)
print(json.dumps({k: out[k] for k in ["buyers_2025", "new_count", "new_share_pct", "vs_true", "gap_months_since_prev_purchase", "month_new_pct_range"]}, ensure_ascii=False, indent=1)); print(yr.round(1))
