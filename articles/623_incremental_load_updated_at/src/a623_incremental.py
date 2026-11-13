"""623 差分の取り込みを「更新日時が前回より後」で行うと、何件が取りこぼされるのか

架空の元の表（2万キー）に、1日で約10万回の更新が入る。updated_at は秒単位で、更新を始めた時刻が入る。
書き込みが確定（コミット）するのは数秒あと（多くは 0〜3秒、5% は 10〜90秒）。取り込みは5分ごとに、確定済みの行だけを読む。
取り込みの条件4通り：
  E1 updated_at > 前回の最大値、E2 updated_at >= 前回の最大値、
  E3 updated_at >= 前回の最大値 − 60秒（重ねて取り、キーで上書き）、E4 コミット順の連番 > 前回の最大値
一度も読まれなかった更新の数、二重に読んだ数、1日の終わりに取り込み先の値が元と違うキーの数を数える。
1回分の取り込みの件数は SQL（DuckDB、1スレッド）でも出し、Python と一致を確かめる。数字は置いた確定の遅れで決まる。
"""
import json
import re
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の更新の記録（作成者が乱数で作成、seed 623）"
rng = np.random.default_rng(623)
DAY, NKEY, EVERY = 86_400, 20_000, 300
# 時間帯で更新の多さが変わる（昼に多い）
hour_w = 0.3 + np.exp(-((np.arange(24) - 14) ** 2) / 18)
lam = hour_w / hour_w.sum() * 100_000
starts = np.concatenate([np.sort(rng.uniform(h * 3600, (h + 1) * 3600, rng.poisson(lam[h]))) for h in range(24)])
N = len(starts)


def make_delay(long_share, rng):
    d = rng.exponential(1.0, N)
    long = rng.random(N) < long_share
    d[long] = rng.uniform(10, 90, long.sum())
    return d


def run(delay, lookback=60):
    L = pd.DataFrame({"event_id": np.arange(N), "row_key": rng_keys, "updated_at": np.floor(starts).astype(int)})
    L["commit_at"] = starts + delay
    L = L.sort_values("commit_at").reset_index(drop=True)
    L["seq"] = np.arange(1, N + 1)
    runs = np.arange(EVERY, DAY + EVERY + 1, EVERY)  # 最後の回は日をまたいだ5分後
    res = {}
    for m in ["E1", "E2", "E3", "E4"]:
        wm, wms = -1, 0
        reads = np.zeros(N, int)
        for t in runs:
            vis = L.commit_at.to_numpy() <= t
            u = L.updated_at.to_numpy(); s = L.seq.to_numpy()
            if m == "E1": sel = vis & (u > wm)
            elif m == "E2": sel = vis & (u >= wm)
            elif m == "E3": sel = vis & (u >= wm - lookback)
            else: sel = vis & (s > wms)
            if sel.any():
                wm = max(wm, int(u[sel].max())); wms = max(wms, int(s[sel].max()))
            reads[sel] += 1
        # 取り込み先：キーごとに、読んだ行のうちコミットの遅いほうが勝つ（上書き）
        rd = L[reads > 0]
        tgt = rd.sort_values("seq").groupby("row_key").event_id.last()
        truth = L.sort_values("seq").groupby("row_key").event_id.last()
        wrong = int((tgt.reindex(truth.index) != truth).sum())
        res[m] = {"never_read": int((reads == 0).sum()), "read_twice_or_more": int((reads >= 2).sum()),
                  "rows_read": int(reads.sum()), "keys_wrong_end_of_day": wrong}
    return L, res


rng_keys = rng.integers(1, NKEY + 1, N)
scen = {}
for share in [0.0, 0.01, 0.05, 0.10]:
    delay = make_delay(share, np.random.default_rng(6230 + int(share * 100)))
    L, r = run(delay)
    scen[share] = r
base_delay = make_delay(0.05, np.random.default_rng(6235))
L5, r5 = run(base_delay)
# 重ねる幅を変える（E3）
lb = {}
for w in [0, 10, 30, 60, 120]:
    _, r = run(base_delay, lookback=w)
    lb[w] = r["E3"]

# SQL で1回分（12時の回）を確かめる
t, wm = 12 * 3600, 12 * 3600 - 300
sub = L5[L5.commit_at <= t]
wm_seq = int(L5[L5.commit_at <= wm].seq.max())
py = [int((sub.updated_at > wm).sum()), int((sub.updated_at >= wm).sum()), int((sub.updated_at >= wm - 60).sum()), int((sub.seq > wm_seq).sum())]
con = duckdb.connect(); con.execute("SET threads=1")
Ls = L5.assign(updated_at=pd.Timestamp("2025-06-02") + pd.to_timedelta(L5.updated_at, unit="s"),
               commit_at=pd.Timestamp("2025-06-02") + pd.to_timedelta(L5.commit_at, unit="s"))
con.register("src_log", Ls)
qs = [q.strip() for q in (SQL / "02_incremental_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in q]
prm = {"run_at": pd.Timestamp("2025-06-02") + pd.Timedelta(seconds=t), "wm": pd.Timestamp("2025-06-02") + pd.Timedelta(seconds=wm), "wm_seq": wm_seq}
sqlc = []
for q in qs:
    body = q[q.index("SELECT"):]
    names = [k for k in prm if re.search(r"\$" + k + r"\b", body)]
    sqlc.append(con.execute(body, {k: prm[k] for k in names}).fetchone()[0])
assert sqlc == py, (sqlc, py)
pd.DataFrame({"method": ["E1", "E2", "E3", "E4"], "python": py, "duckdb": sqlc}).to_csv(RES / "sql_one_run.csv", index=False)

rows = []
for share, r in scen.items():
    for m, v in r.items():
        rows.append({"long_delay_share": share, "method": m, **v})
S = pd.DataFrame(rows); S.to_csv(RES / "summary.csv", index=False)
LB = pd.DataFrame([{"lookback_sec": w, **v} for w, v in lb.items()]); LB.to_csv(RES / "lookback_e3.csv", index=False)
out = {"events": N, "keys": NKEY, "every_sec": EVERY, "by_long_delay_share": {str(k): v for k, v in scen.items()},
       "lookback_e3_at_5pct": LB.to_dict(orient="records"), "sql_check_12h": dict(zip(["E1", "E2", "E3", "E4"], py))}
json.dump(out, open(RES / "a623_main.json", "w"), ensure_ascii=False, indent=1)

LAB = {"E1": "updated_at ＞ 前回の最大", "E2": "updated_at ≧ 前回の最大", "E3": "60秒重ねて取る", "E4": "コミット順の連番"}
COL = {"E1": ORANGE, "E2": BLUE, "E3": GREEN, "E4": INK}
# 図1
fig, ax = plt.subplots(figsize=(8.5, 4.2))
xs = np.arange(4); w = 0.2
for j, m in enumerate(["E1", "E2", "E3", "E4"]):
    v = [scen[s][m]["never_read"] for s in scen]
    ax.bar(xs + (j - 1.5) * w, v, w, color=COL[m], label=LAB[m])
    for x, vv in zip(xs + (j - 1.5) * w, v):
        ax.text(x, vv, f"{vv:,}", ha="center", va="bottom", fontsize=7.5)
ax.set_xticks(xs); ax.set_xticklabels([f"{int(s*100)}%" for s in scen]); ax.set_xlabel("確定が10〜90秒遅れる更新の割合")
ax.set_ylabel("一度も取り込まれなかった更新（件）"); ax.legend(frameon=False, fontsize=9)
ax.set_title(f"1日 {N:,}件の更新のうち、取りこぼした件数")
save(fig, "a623_never_read.png", SRC)

# 図2：5% のときの、取りこぼし・二重・日末のずれ
fig, ax = plt.subplots(1, 3, figsize=(11.5, 3.8), gridspec_kw={"wspace": 0.6})
ms = ["E1", "E2", "E3", "E4"]
for i, (k, tt) in enumerate([("never_read", "取りこぼした更新"), ("read_twice_or_more", "二重に読んだ更新"), ("keys_wrong_end_of_day", "日の終わりに値が違うキー")]):
    v = [r5[m][k] for m in ms]
    ax[i].barh([LAB[m] for m in ms][::-1], v[::-1], color=[COL[m] for m in ms][::-1])
    for y, vv in enumerate(v[::-1]):
        ax[i].text(vv, y, f" {vv:,}", va="center", fontsize=8.5)
    ax[i].set_title(tt, fontsize=11); ax[i].set_xlim(0, max(max(v), 1) * 1.5)
    if i: ax[i].set_yticklabels([])
save(fig, "a623_breakdown.png", SRC, y=-0.05)

# 図3：重ねる幅
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(LB.lookback_sec, LB.never_read, marker="o", color=ORANGE, label="取りこぼした更新")
ax.plot(LB.lookback_sec, LB.read_twice_or_more, marker="s", color=BLUE, label="二重に読んだ更新")
for x, y in zip(LB.lookback_sec, LB.never_read):
    ax.text(x, y, f" {y:,}", fontsize=8.5, color=ORANGE, va="bottom")
ax.set_xlabel("重ねて取る幅（秒）"); ax.set_ylabel("件数"); ax.legend(frameon=False, fontsize=9)
ax.set_title("重ねる幅を広げると取りこぼしは減り、二重は増える（遅れ10〜90秒が5%）")
save(fig, "a623_lookback.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
