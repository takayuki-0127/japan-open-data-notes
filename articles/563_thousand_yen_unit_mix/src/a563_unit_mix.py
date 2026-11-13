"""563 千円単位と円単位の数字が混ざった表から、桁のずれた行をどう見つけるのか

架空の部門別の月次経費表（60部門 × 2023年1月〜2025年12月の36か月、円単位）。一部の行を千円単位で入れてしまった、とする：
  ぽつんと1か月だけ千円単位：40行
  数か月続けて千円単位（3〜6か月）：8部門
  ある部門はずっと千円単位：2部門
本当に大きく動いた月（臨時の支出で5〜20倍、休止で0.002〜0.1倍）も混ぜる。
見つけ方を3通り比べる：
  M1 前月比：前月の1/100以下なら桁ずれとする
  M2 中央値との倍率：その部門の36か月の中央値の1/100以下なら桁ずれとする
  M3 合計との照合：別に分かっている全社の月合計と合わないとき、×1000で合う行（1〜3行の組）を探す
  M2→M3：M2 で見つけた行を直してから、残りの差を M3 で探す
見つけた件数・見逃した件数・誤って見つけた件数を、作成者が付けた正解で数える。
SQL（DuckDB、1スレッド）で M1・M2 を書き、Python と結果が一致することを確かめる。数字は置いた仮定で決まる。
"""
import json
from itertools import combinations
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空の部門別の月次経費（作成者が乱数で作成、seed 563）"
rng = np.random.default_rng(563)
ND, NM = 60, 36
months = pd.period_range("2023-01", periods=NM, freq="M")
depts = [f"D{i:02d}" for i in range(1, ND + 1)]
level = np.exp(rng.uniform(np.log(3e5), np.log(8e7), ND))     # 部門の規模
season = 1 + 0.12 * np.sin(2 * np.pi * (np.arange(NM) + 3) / 12)
true = np.round(level[:, None] * season[None, :] * np.exp(rng.normal(0, 0.18, (ND, NM)))).astype(np.int64)
kind = np.full((ND, NM), "", dtype=object)
# 本当に大きく動いた月（正しい値）
for _ in range(18):
    d, m = rng.integers(ND), rng.integers(NM)
    true[d, m] = int(true[d, m] * rng.uniform(5, 20)); kind[d, m] = "本当に大きい"
for _ in range(12):
    d, m = rng.integers(ND), rng.integers(NM)
    true[d, m] = int(true[d, m] * np.exp(rng.uniform(np.log(0.002), np.log(0.1)))); kind[d, m] = "本当に小さい"
err = np.zeros((ND, NM), dtype=object); err[:] = ""
whole = rng.choice(ND, 2, replace=False)
for d in whole:
    err[d, :] = "ずっと"
others = [d for d in range(ND) if d not in whole]
runs = rng.choice(others, 8, replace=False)
for d in runs:
    L = rng.integers(3, 7); s = rng.integers(1, NM - L)
    err[d, s:s + L] = "続けて"
cand = [(d, m) for d in others for m in range(NM) if err[d, m] == "" and kind[d, m] == ""]
for i in rng.choice(len(cand), 40, replace=False):
    err[cand[i]] = "1か月だけ"
entered = true.copy()
mask = err != ""
entered[mask] = np.round(true[mask] / 1000).astype(np.int64)

rows = []
for d in range(ND):
    for m in range(NM):
        rows.append((depts[d], str(months[m]), int(entered[d, m]), int(true[d, m]), err[d, m], kind[d, m]))
T = pd.DataFrame(rows, columns=["dept", "month", "amount", "true_amount", "error_type", "true_move"])
T[["dept", "month", "amount"]].to_csv(DATA / "dept_monthly.csv", index=False)
tot = T.groupby("month").true_amount.sum().rename("reported_total").reset_index()
tot.to_csv(DATA / "monthly_total.csv", index=False)
T[["dept", "month", "true_amount", "error_type", "true_move"]].to_csv(DATA / "dept_monthly_truth.csv", index=False)

# M1 前月比
T = T.sort_values(["dept", "month"]).reset_index(drop=True)
T["prev"] = T.groupby("dept").amount.shift()
T["m1"] = (T.amount <= T.prev / 100)
# M2 中央値との倍率
T["med"] = T.groupby("dept").amount.transform("median")
T["m2"] = (T.amount <= T.med / 100)
# M3 合計との照合：月ごとに、合計の差を ×1000 で埋める行の組（1〜3行）を探す
TOT = tot.set_index("month").reported_total


def m3(fixed):
    """fixed：先に直した行（True の行は ×1000 してから照合する）。戻り値：見つけた行、解けなかった月の数"""
    flag = pd.Series(False, index=T.index)
    unresolved = 0
    for mo, g in T.groupby("month"):
        vals = np.where(fixed.loc[g.index], g.amount.values * 1000, g.amount.values)
        gap = int(TOT.loc[mo]) - int(vals.sum())
        if abs(gap) <= 600 * int(fixed.loc[g.index].sum()):     # 直した行の丸めの分だけ許す
            continue
        cand = [i for i in range(len(vals)) if not fixed.loc[g.index[i]] and 999 * vals[i] <= gap * 1.001 + 1000]
        found = None
        for k in (1, 2, 3):
            best = None
            for comb in combinations(cand, k):
                add = 999 * vals[list(comb)].sum()
                if abs(gap - add) <= 600 * (k + int(fixed.loc[g.index].sum())):
                    if best is None or abs(gap - add) < best[0]:
                        best = (abs(gap - add), comb)
            if best:
                found = best[1]; break
        if found is not None:
            flag.loc[g.index[list(found)]] = True
        else:
            unresolved += 1
    return flag, unresolved


T["m3"], M3_UNRES = m3(pd.Series(False, index=T.index))
f23, M23_UNRES = m3(T.m2)
T["m2m3"] = T.m2 | f23

T["is_err"] = T.error_type != ""


def score(col):
    out = {}
    for et in ["1か月だけ", "続けて", "ずっと"]:
        q = T[T.error_type == et]
        out[et] = {"rows": len(q), "found": int(q[col].sum())}
    out["found_total"] = int((T[col] & T.is_err).sum())
    out["missed_total"] = int((~T[col] & T.is_err).sum())
    out["false_positive"] = int((T[col] & ~T.is_err).sum())
    out["false_positive_true_move"] = int((T[col] & ~T.is_err & (T.true_move != "")).sum())
    return out


SC = {c: score(c) for c in ["m1", "m2", "m3", "m2m3"]}

# 直さないときの月合計のずれ
mt = T.groupby("month").agg(entered=("amount", "sum"), true=("true_amount", "sum")).reset_index()
mt["diff_pct"] = 100 * (mt.entered / mt.true - 1)
mt.to_csv(RES / "monthly_total_gap.csv", index=False)
T[["dept", "month", "amount", "error_type", "true_move", "m1", "m2", "m3", "m2m3"]].to_csv(RES / "flags.csv", index=False)

# SQL（DuckDB）で M1・M2
con = duckdb.connect()
con.execute("SET threads=1")
con.execute(f"CREATE TABLE dept_monthly AS SELECT * FROM read_csv_auto('{DATA / 'dept_monthly.csv'}', types={{'month':'VARCHAR'}})")
q = con.execute((SQL / "02_detect_duckdb.sql").read_text()).df().sort_values(["dept", "month"]).reset_index(drop=True)
assert (q.m1.fillna(False).astype(bool).values == T.m1.values).all()
assert (q.m2.astype(bool).values == T.m2.values).all()

summary = {"rows": len(T), "error_rows": int(T.is_err.sum()), "error_by_type": T[T.is_err].error_type.value_counts().to_dict(),
           "true_moves": T[T.true_move != ""].true_move.value_counts().to_dict(),
           "scores": SC, "months_with_gap": int((mt.diff_pct.abs() > 0).sum()),
           "monthly_total_diff_pct": {"min": round(float(mt.diff_pct.min()), 2), "max": round(float(mt.diff_pct.max()), 2), "mean": round(float(mt.diff_pct.mean()), 2)},
           "m3_months_unresolved": M3_UNRES, "m2then3_months_unresolved": M23_UNRES,
           "sql_python_match_m1_m2": True}
json.dump(summary, open(RES / "a563_main.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))

# 図1：例の部門
fig, axs = plt.subplots(1, 3, figsize=(11, 3.6), sharey=False)
ex = [("1か月だけ", next(d for d in others if (err[d] == "1か月だけ").any() and d not in runs)), ("続けて", runs[0]), ("ずっと", whole[0])]
for ax, (lab, d) in zip(axs, ex):
    x = np.arange(NM)
    ax.plot(x, true[d], color=GRAY, lw=1.2, label="正しい値")
    ax.plot(x, entered[d], color=BLUE, lw=1.4, marker="o", ms=2.5, label="表の値")
    e = err[d] != ""
    ax.scatter(x[e], entered[d][e], color=ORANGE, s=22, zorder=3, label="千円単位の行")
    ax.set_yscale("log"); ax.set_title(f"{depts[d]}：{lab}", loc="left", fontsize=11)
    ax.set_xticks([0, 12, 24, 35], ["23/1", "24/1", "25/1", "25/12"])
axs[0].set_ylabel("経費（円、対数目盛）")
axs[0].legend(frameon=False, fontsize=8)
fig.suptitle("千円単位の行は、対数目盛で3けた下に落ちる", x=0.01, ha="left", fontsize=13)
fig.tight_layout()
save(fig, "a563_examples.png", SRC)

# 図2：見つけた・見逃した・誤って見つけた
fig, ax = plt.subplots(figsize=(9, 4.2))
labs = {"m1": "M1 前月比", "m2": "M2 中央値との倍率", "m3": "M3 合計との照合", "m2m3": "M2→M3"}
types = ["1か月だけ", "続けて", "ずっと"]
cols = [ORANGE, BLUE, GREEN]
xs = np.arange(4)
bottom = np.zeros(4)
for t, c in zip(types, cols):
    v = np.array([SC[k][t]["found"] for k in labs])
    ax.bar(xs - 0.2, v, 0.4, bottom=bottom, color=c, label=f"見つけた：{t}")
    bottom += v
miss = np.array([SC[k]["missed_total"] for k in labs])
fp = np.array([SC[k]["false_positive"] for k in labs])
ax.bar(xs + 0.2, miss, 0.4, color=LIGHT, label="見逃した")
ax.bar(xs + 0.2, fp, 0.4, bottom=miss, color=GRAY, label="誤って見つけた")
for i in range(4):
    ax.text(xs[i] - 0.2, bottom[i] + 3, f"{int(bottom[i])}", ha="center", fontsize=9)
    ax.text(xs[i] + 0.2, miss[i] + fp[i] + 3, f"{miss[i]}／{fp[i]}", ha="center", fontsize=9)
ax.axhline(int(T.is_err.sum()), color=INK, lw=0.8, ls="--")
ax.text(3.5, int(T.is_err.sum()) + 2, f"桁ずれ {int(T.is_err.sum())}行", ha="right", fontsize=9)
ax.set_xticks(xs, list(labs.values()))
ax.set_ylabel("行の数")
ax.set_title("見つけ方ごとの、見つけた行・見逃した行・誤って見つけた行", loc="left")
ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.1))
save(fig, "a563_detect.png", SRC, y=-0.2)

# 図3：直さないときの月合計のずれ
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.bar(np.arange(NM), mt.diff_pct, color=BLUE)
ax.set_xticks([0, 12, 24, 35], ["2023/1", "2024/1", "2025/1", "2025/12"])
ax.set_ylabel("全社の月合計のずれ（%）")
ax.set_title("直さずに足すと、月合計は毎月少なく出る", loc="left")
save(fig, "a563_total_gap.png", SRC)
