"""455 1ページずつ順に取り込むと、途中で行が増減したとき、何行が重なり、何行が抜けるのか
架空の一覧（取り込み中に追加と削除が起きる）で、ページの送り方3つを比べる（seed 455）。
同じ手順を SQLite の SQL（LIMIT/OFFSET、キーの続き）でも流して、数が一致することを確かめる。"""
import json, sqlite3
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import RES, BLUE, ORANGE, GRAY, GREEN, save

SEED = 455


def ingest(method, order, n0, page, ins_pct, del_pct, seed, sql=False):
    """n0 行の一覧を page 行ずつ取り込む。1ページ取るごとに、追加と削除が起きる。
    ins_pct・del_pct は、取り込みの間（n0/page ページ分）に起きる追加・削除の、最初の行数に対する%。
    method: offset（何行目から）／keyset（キーの続きから）／snapshot（開始時点の最大のキーまでに限る＋キーの続き）
    order: asc（古い順）／desc（新しい順）"""
    rng = np.random.default_rng(seed)
    alive = np.arange(1, n0 + 1)                               # キーは作られた順の番号
    next_id = n0 + 1
    start_ids = alive.copy(); max_at_start = n0
    pages = int(np.ceil(n0 / page))
    ins_per = ins_pct / 100 * n0 / pages; del_per = del_pct / 100 * n0 / pages
    got = []; offset = 0; last = None
    con = None
    if sql:
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE t(id INTEGER PRIMARY KEY)")
        con.executemany("INSERT INTO t VALUES (?)", [(int(x),) for x in alive])
    for _ in range(pages * 3 + 10):
        # ---- 1ページ取る ----
        if sql:
            od = "ASC" if order == "asc" else "DESC"
            if method == "offset":
                rows = [r[0] for r in con.execute(f"SELECT id FROM t ORDER BY id {od} LIMIT ? OFFSET ?", (page, offset))]
            else:
                cond = []; par = []
                if method == "snapshot":
                    cond.append("id <= ?"); par.append(max_at_start)
                if last is not None:
                    cond.append("id > ?" if order == "asc" else "id < ?"); par.append(int(last))
                w = ("WHERE " + " AND ".join(cond)) if cond else ""
                rows = [r[0] for r in con.execute(f"SELECT id FROM t {w} ORDER BY id {od} LIMIT ?", (*par, page))]
            rows = np.array(rows, dtype=np.int64)
        else:
            if method == "offset":
                rows = (alive if order == "asc" else alive[::-1])[offset:offset + page]
            else:                                              # alive はいつもキーの小さい順に並んでいる
                top = np.searchsorted(alive, max_at_start, side="right") if method == "snapshot" else len(alive)
                if order == "asc":
                    lo = 0 if last is None else np.searchsorted(alive, last, side="right")
                    rows = alive[lo:min(lo + page, top)]
                else:
                    hi = top if last is None else min(np.searchsorted(alive, last, side="left"), top)
                    rows = alive[max(hi - page, 0):hi][::-1]
        if len(rows) == 0:
            break
        got.append(np.array(rows)); offset += page; last = rows[-1]
        if len(rows) < page:                                   # 行数がページに満たなければ、そこで終わり
            break
        # ---- 取り込みの間に起きる変化 ----
        n_del = rng.poisson(del_per); n_ins = rng.poisson(ins_per)
        if n_del:
            ix = rng.choice(len(alive), min(n_del, len(alive)), replace=False)
            d = alive[ix]; alive = np.delete(alive, ix)
            if sql:
                con.executemany("DELETE FROM t WHERE id = ?", [(int(x),) for x in d])
        if n_ins:
            new = np.arange(next_id, next_id + n_ins); next_id += n_ins
            alive = np.concatenate([alive, new])
            if sql:
                con.executemany("INSERT INTO t VALUES (?)", [(int(x),) for x in new])
    got = np.concatenate(got) if got else np.array([], dtype=np.int64)
    M = next_id + 1
    c = np.bincount(got, minlength=M)                          # キーごとの、取り込んだ回数
    alive_m = np.zeros(M, bool); alive_m[alive] = True
    start_m = np.zeros(M, bool); start_m[1:n0 + 1] = True
    stable_m = start_m & alive_m                               # 最初から最後まであった行
    out = {"fetched": int(len(got)), "dup_rows": int((c > 1).sum()), "missed_stable": int((stable_m & (c == 0)).sum()),
           "stale_rows": int(((c > 0) & ~alive_m).sum()),       # 取り込んだが、終わりにはもうない行
           "new_missed": int((alive_m & ~start_m & (c == 0)).sum()),
           "source_at_end": int(len(alive)), "stable": int(stable_m.sum())}
    out["count_diff"] = out["fetched"] - out["source_at_end"]
    return out


METHODS = [("offset", "asc", "何行目から（古い順）"), ("offset", "desc", "何行目から（新しい順）"),
           ("keyset", "asc", "キーの続きから（古い順）"), ("keyset", "desc", "キーの続きから（新しい順）"),
           ("snapshot", "asc", "開始時点で固定（古い順）")]
N0, PAGE, REPS = 100_000, 1000, 30


def run(method, order, n0=N0, page=PAGE, ins=1.0, dele=1.0, reps=REPS):
    d = pd.DataFrame([ingest(method, order, n0, page, ins, dele, SEED + 100 * k) for k in range(reps)])
    r = {c: round(float(d[c].mean()), 1) for c in d.columns}
    bad = (d.dup_rows + d.missed_stable) > 0
    r["runs_with_error_pct"] = round(100 * float(bad.mean()), 1)
    r["count_check_misses_pct"] = round(100 * float((bad & (d.count_diff == 0)).sum() / max(bad.sum(), 1)), 1)   # 件数が合ってしまう割合
    r["count_diff_abs_mean"] = round(float(d.count_diff.abs().mean()), 1)
    return r


# ---------- SQLite の SQL と一致するか（小さい表） ----------
chk = []
for m, o, lab in METHODS:
    a = ingest(m, o, 5000, 100, 2.0, 2.0, SEED); b = ingest(m, o, 5000, 100, 2.0, 2.0, SEED, sql=True)
    assert a == b, (lab, a, b)
    chk.append({"method": lab, "same_as_sql": a == b, **a})
pd.DataFrame(chk).to_csv(RES / "sqlite_check.csv", index=False)

# ---------- 基本の場面：追加1%・削除1% ----------
base = pd.DataFrame([{"method": lab, **run(m, o)} for m, o, lab in METHODS]); base.to_csv(RES / "base_methods.csv", index=False)

# ---------- 追加・削除の割合を変える ----------
rates = []
for ins, dele in ((0.1, 0.1), (1, 0), (0, 1), (1, 1), (5, 5), (5, 1)):
    for m, o, lab in METHODS[:2]:
        rates.append({"ins_pct": ins, "del_pct": dele, "method": lab, **run(m, o, ins=ins, dele=dele)})
rates = pd.DataFrame(rates); rates.to_csv(RES / "by_change_rate.csv", index=False)

# ---------- ページの大きさを変える ----------
pg = []
for page in (1000, 5000, 20000, 50000):
    for m, o, lab in METHODS[:2]:
        pg.append({"page": page, "method": lab, **run(m, o, page=page)})
pg = pd.DataFrame(pg); pg.to_csv(RES / "by_page_size.csv", index=False)

main = {"seed": SEED, "n0": N0, "page": PAGE, "reps": REPS, "base": base.to_dict(orient="records"), "by_change_rate": rates.to_dict(orient="records"),
        "by_page_size": pg.to_dict(orient="records"), "sqlite_check_all_same": True}
json.dump(main, open(RES / "a455_main.json", "w"), ensure_ascii=False, indent=1)

# ---------- 図 ----------
SRC = "架空のデータ（取り込み中の追加と削除を乱数で作るシミュレーション、seed 455。30回の平均）"
fig, ax = plt.subplots(figsize=(8.8, 4.2))
y = np.arange(len(base)); b = base.iloc[::-1].reset_index(drop=True)
ax.barh(y - 0.2, b.dup_rows, 0.4, color=BLUE, label="重なった行（2回以上取り込んだ行）")
ax.barh(y + 0.2, b.missed_stable, 0.4, color=ORANGE, label="抜けた行（最初から最後まであったのに取り込まれなかった行）")
for i, (d, m) in enumerate(zip(b.dup_rows, b.missed_stable)):
    ax.text(d + 8, i - 0.2, f"{d:,.0f}", va="center", fontsize=9); ax.text(m + 8, i + 0.2, f"{m:,.0f}", va="center", fontsize=9)
ax.set_yticks(y); ax.set_yticklabels(b.method, fontsize=9.5); ax.set_xlabel("行の数（10万行の一覧、取り込み中に追加1%・削除1%）")
ax.set_xlim(0, max(b.dup_rows.max(), b.missed_stable.max()) * 1.2 + 10)
ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.45, -0.16)); ax.set_title("ページの送り方ごとの、重なった行と抜けた行")
save(fig, "a455_methods.png", SRC, y=-0.16)

fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), sharey=True)
for ax, lab in zip(axes, ("何行目から（古い順）", "何行目から（新しい順）")):
    t = rates[rates.method == lab].reset_index(drop=True); x = np.arange(len(t)); wd = 0.38
    ax.bar(x - wd / 2, t.dup_rows, wd, color=BLUE, label="重なった行"); ax.bar(x + wd / 2, t.missed_stable, wd, color=ORANGE, label="抜けた行")
    ax.set_xticks(x); ax.set_xticklabels([f"追加{a:g}%\n削除{d:g}%" for a, d in zip(t.ins_pct, t.del_pct)], fontsize=8); ax.set_title(lab, fontsize=11)
axes[0].set_ylabel("行の数"); axes[0].legend(frameon=False, fontsize=9)
fig.suptitle("追加と削除の割合ごとの、重なった行と抜けた行（何行目から、で区切る）", fontsize=12, y=1.03)
save(fig, "a455_by_change_rate.png", SRC)

fig, ax = plt.subplots(figsize=(8.8, 4.2))
t = base.copy(); x = np.arange(len(t))
ax.bar(x, t.count_diff, color=[ORANGE, ORANGE, BLUE, BLUE, BLUE])
ax.axhline(0, color=GRAY, lw=1)
for i, (v, d, m) in enumerate(zip(t.count_diff, t.dup_rows, t.missed_stable)):
    ax.text(i, v + (25 if v >= 0 else -25), f"差 {v:+,.0f}\n（重なり {d:,.0f}・抜け {m:,.0f}）", ha="center", va="bottom" if v >= 0 else "top", fontsize=8.5)
ax.set_xticks(x); ax.set_xticklabels([m.replace("（", "\n（") for m in t.method], fontsize=8.5); ax.set_ylabel("取り込んだ行数 − 終わりの時点の行数")
ax.set_ylim(-750, 750); ax.set_title("件数の照合で見える差（追加1%・削除1%）")
save(fig, "a455_count_check.png", SRC)
pd.set_option("display.width", 250)
print(base.to_string()); print(rates.to_string()); print(pg.to_string())
