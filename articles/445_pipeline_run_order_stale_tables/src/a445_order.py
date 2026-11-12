"""445 順番に動かすはずの集計を、順番を違えて流すと、何枚の表が古い数字のままになるか（架空の20枚の表）"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

SEED = 445
SRC = "架空の集計の流れ（作成者が乱数で作成、seed 445）"
# 20枚の表：取り込み5枚（s1〜s5）、中間8枚（m1〜m8）、レポート用7枚（r1〜r7）
DEPS = {"m1": ["s1"], "m2": ["s1", "s2"], "m3": ["s2"], "m4": ["s3"], "m5": ["s3", "s4"], "m6": ["s5"], "m7": ["m1", "m2"], "m8": ["m4", "m5"],
        "r1": ["m1"], "r2": ["m7"], "r3": ["m3", "m7"], "r4": ["m8"], "r5": ["m6", "m8"], "r6": ["m7", "m8"], "r7": ["r2", "r4"]}
TABLES = [f"s{i}" for i in range(1, 6)] + [f"m{i}" for i in range(1, 9)] + [f"r{i}" for i in range(1, 8)]
for t in TABLES: DEPS.setdefault(t, [])
IDX = {t: i for i, t in enumerate(TABLES)}
pd.DataFrame([(t, d) for t in TABLES for d in DEPS[t]], columns=["table_name", "depends_on"]).to_csv(DATA / "deps.csv", index=False)
pd.DataFrame({"table_name": TABLES}).to_csv(DATA / "tables.csv", index=False)


def level(t, memo={}):
    if t not in memo: memo[t] = 0 if not DEPS[t] else 1 + max(level(d) for d in DEPS[t])
    return memo[t]


LV = {t: level(t) for t in TABLES}
TOPO = sorted(TABLES, key=lambda t: (LV[t], t))           # 依存の定義から作った正しい順（段ごと）
SEQ = ["s1", "m1", "r1", "s2", "m2", "m3", "m7", "r2", "r3", "s3", "m4", "s4", "m5", "m8", "r4", "r7", "s5", "m6", "r5", "r6"]   # 手で書いた正しい順（関係のある表を続けて流す）
assert sorted(SEQ) == sorted(TABLES) and all(SEQ.index(d) < SEQ.index(t) for t in TABLES for d in DEPS[t])
DOWN = {t: set() for t in TABLES}                         # その表の下流（直接・間接）
for t in TABLES:
    stack = list(DEPS[t])
    while stack:
        u = stack.pop(); DOWN[u].add(t); stack += DEPS[u]


def run(start, dur):
    """各表は start[t] に読みはじめ、start[t]+dur[t] にできあがる。読んだ時点で上流がまだできていなければ、上流の前の日の版を読む。
    戻り値：(古い数字が残る表, できあがり時刻の検査で見つかる表, データの日付の検査で見つかる表)"""
    fin = {t: start[t] + dur[t] for t in TABLES}
    ver = {}                                              # その表の数字が何日前のものか（0=今日, -1=1日前…）。毎日同じ流し方をくり返すとして数える
    stale_direct = {}
    for t in TOPO:
        v = 0; direct = False
        for d in DEPS[t]:
            if fin[d] > start[t]:                         # 上流がまだできていない → 上流の前の日の版を読む
                v = min(v, ver[d] - 1); direct = True
            else:
                v = min(v, ver[d])
        ver[t] = v; stale_direct[t] = direct
    run.lag = -min(ver.values())
    stale = {t for t in TABLES if ver[t] < 0}
    by_finish = {t for t in TABLES if any(fin[t] < fin[d] for d in DEPS[t])}                 # 「自分のできあがりが上流より早い」
    by_start = {t for t in TABLES if any(start[t] < fin[d] for d in DEPS[t])}                # 「自分の読みはじめが上流のできあがりより早い」
    by_date = {t for t in TABLES if any(ver[t] < ver[d] for d in DEPS[t])}                   # 「自分のデータの日付が上流より古い」（直接の原因の表）
    return stale, by_finish, by_start, by_date, {t for t in TABLES if stale_direct[t]}


def seq_schedule(order, dur):
    s, t0 = {}, 0.0
    for t in order: s[t] = t0; t0 += dur[t]
    return s


r = np.random.default_rng(SEED)
BASE = {t: (20 if t[0] == "s" else 12 if t[0] == "m" else 6) for t in TABLES}       # ふだんの所要（分）
def durs(): return {t: BASE[t] * r.lognormal(0, 0.25) for t in TABLES}


assert run(seq_schedule(TOPO, {t: BASE[t] for t in TABLES}), {t: BASE[t] for t in TABLES})[0] == set() and run(seq_schedule(SEQ, {t: BASE[t] for t in TABLES}), {t: BASE[t] for t in TABLES})[0] == set()
N = 1000; rows = []
def rec(case, out):
    stale, bf, bs, bd, direct = out
    rows.append(dict(case=case, lag=run.lag, stale=len(stale), direct=len(direct), any_stale=int(len(stale) > 0), found_finish=int(len(bf & direct) > 0) if direct else np.nan, found_finish_all=int(direct <= bf) if direct else np.nan,
                     found_start=int(direct <= bs) if direct else np.nan, found_date=int(direct <= bd) if direct else np.nan, reports_stale=len([t for t in stale if t[0] == "r"])))


for k in range(N):
    d = durs()
    rec("正しい順に1つずつ", run(seq_schedule(SEQ, d), d))                                   # ① 定義から作った順
    o = SEQ.copy(); i = r.integers(0, len(o) - 1); o[i], o[i + 1] = o[i + 1], o[i]
    rec("となりの2枚が入れ替わる", run(seq_schedule(o, d), d))                                # ② 1か所だけ前後する
    o = SEQ.copy(); i, j = r.choice(len(o), 2, replace=False); o[i], o[j] = o[j], o[i]
    rec("はなれた2枚が入れ替わる", run(seq_schedule(o, d), d))                                # ③
    o = list(r.permutation(TABLES)); rec("でたらめな順", run(seq_schedule(o, d), d))          # ④
    # ⑤ 時刻で並行に流す：段ごとの開始時刻を「ふだんの所要＋余裕」で決め打ち
    for margin, lab in ((1.0, "並行（開始時刻を決め打ち、余裕なし）"), (1.3, "並行（余裕3割）"), (1.6, "並行（余裕6割）")):
        t0 = {0: 0.0}; t0[1] = 20 * margin; t0[2] = t0[1] + 12 * margin; t0[3] = t0[2] + 12 * margin; t0[4] = t0[3] + 6 * margin
        rec(lab, run({t: t0[LV[t]] for t in TABLES}, d))
    # ⑥ 並行だが、上流ができあがってから始める（依存の定義を見て待つ）
    st = {}; fin = {}
    for t in TOPO: st[t] = max([fin[x] for x in DEPS[t]], default=0.0); fin[t] = st[t] + d[t]
    rec("並行（上流のできあがりを待つ）", run(st, d)); rows[-1]["elapsed"] = max(fin.values())
    rows[-8]["elapsed"] = sum(d.values())
R = pd.DataFrame(rows); R.to_csv(RES / "trials_1000.csv", index=False)
S = R.groupby("case", sort=False).agg(any_stale=("any_stale", lambda x: x.mean() * 100), stale_mean=("stale", "mean"), stale_mean_when_any=("stale", lambda x: x[x > 0].mean() if (x > 0).any() else 0.0),
                                      stale_max=("stale", "max"), lag_max=("lag", "max"), lag2_share=("lag", lambda x: (x >= 2).mean() * 100), reports_stale=("reports_stale", "mean"), found_finish=("found_finish_all", lambda x: x.mean() * 100), found_start=("found_start", lambda x: x.mean() * 100),
                                      found_date=("found_date", lambda x: x.mean() * 100), elapsed=("elapsed", "mean")).reset_index()
S.round(2).to_csv(RES / "summary_by_case.csv", index=False)

# どの2枚が入れ替わると、何枚が古くなるか（となりの入れ替え19通り、所要はふだんどおり）
d0 = {t: float(BASE[t]) for t in TABLES}; rows = []
for i in range(len(SEQ) - 1):
    o = SEQ.copy(); o[i], o[i + 1] = o[i + 1], o[i]; out = run(seq_schedule(o, d0), d0)
    rows.append(dict(pos=i + 1, swapped=f"{SEQ[i]}⇄{SEQ[i + 1]}", depends=int(SEQ[i] in DEPS[SEQ[i + 1]]), stale=len(out[0]), stale_tables=" ".join(sorted(out[0], key=IDX.get)), found_finish=int(out[4] <= out[1]) if out[4] else ""))
SW = pd.DataFrame(rows); SW.to_csv(RES / "adjacent_swaps.csv", index=False)
# 1枚だけ遅れたとき（並行・開始時刻の決め打ち・余裕3割）：どの表が何倍遅れると、何枚が古くなるか
rows = []
for t in TABLES:
    for mult in (1.5, 2.0, 3.0):
        d = dict(d0); d[t] *= mult; t0 = {0: 0.0, 1: 26.0, 2: 41.6, 3: 57.2, 4: 65.0}
        out = run({x: t0[LV[x]] for x in TABLES}, d); rows.append(dict(table=t, mult=mult, stale=len(out[0]), downstream=len(DOWN[t]), found_finish=(int(out[4] <= out[1]) if out[4] else "")))
LT = pd.DataFrame(rows); LT.to_csv(RES / "one_table_late.csv", index=False)

# SQL（DuckDB）で段を出して一致を確かめる
con = duckdb.connect(); con.execute("SET threads=1"); con.register("deps", pd.read_csv(DATA / "deps.csv")); con.register("tables", pd.read_csv(DATA / "tables.csv"))
q = """WITH RECURSIVE lv AS (SELECT t.table_name, 0 AS lvl FROM tables t WHERE NOT EXISTS (SELECT 1 FROM deps d WHERE d.table_name = t.table_name)
       UNION ALL SELECT d.table_name, lv.lvl + 1 FROM deps d JOIN lv ON lv.table_name = d.depends_on)
       SELECT table_name, MAX(lvl) AS run_level FROM lv GROUP BY table_name ORDER BY run_level, table_name"""
sq = con.execute(q).df(); assert dict(zip(sq.table_name, sq.run_level)) == LV and list(sq.table_name) == TOPO
sq.to_csv(RES / "sql_check_duckdb.csv", index=False)

g = lambda c, col: float(S[S.case == c][col].iloc[0])
main = dict(n_tables=len(TABLES), n_deps=sum(len(v) for v in DEPS.values()), levels=max(LV.values()) + 1, trials=N, summary=json.loads(S.round(2).to_json(orient="records", force_ascii=False)),
            adjacent=dict(n=len(SW), with_dependency=int(SW.depends.sum()), stale_when_dep=SW[SW.depends == 1][["swapped", "stale"]].to_dict("records"), found_finish_when_dep=int((SW[SW.depends == 1].found_finish == 1).sum())),
            late=dict(by_mult={str(m): dict(cases_with_stale=int((LT[LT.mult == m].stale > 0).sum()), mean_stale=float(LT[LT.mult == m].stale.mean()), max_stale=int(LT[LT.mult == m].stale.max()),
                                            found_finish=int((LT[(LT.mult == m) & (LT.stale > 0)].found_finish == 1).sum())) for m in (1.5, 2.0, 3.0)}),
            downstream={t: len(DOWN[t]) for t in TABLES})
json.dump(main, open(RES / "a445_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：依存の図（段ごとに並べる）
fig, ax = plt.subplots(figsize=(10, 4.6)); pos = {}
for lv in range(max(LV.values()) + 1):
    ts = [t for t in TOPO if LV[t] == lv]
    for j, t in enumerate(ts): pos[t] = (lv, (len(ts) - 1) / 2 - j)
for t in TABLES:
    for d in DEPS[t]: ax.annotate("", xy=(pos[t][0] - 0.13, pos[t][1]), xytext=(pos[d][0] + 0.13, pos[d][1]), arrowprops=dict(arrowstyle="->", color=GRAY, lw=0.9))
for t, (x, y) in pos.items():
    ax.text(x, y, t, ha="center", va="center", fontsize=10, bbox=dict(boxstyle="round,pad=0.35", fc=LIGHT if t[0] == "s" else "white" if t[0] == "m" else "#f6c9b4", ec=INK, lw=0.8))
ax.set_xlim(-0.5, max(LV.values()) + 0.5); ax.set_ylim(-3.6, 3.6); ax.set_xticks(range(max(LV.values()) + 1)); ax.set_xticklabels([f"{i + 1}段目" for i in range(max(LV.values()) + 1)]); ax.set_yticks([])
for sp in ax.spines.values(): sp.set_visible(False)
ax.set_title("架空の集計の流れ：20枚の表と、読む・読まれるの関係（矢印の先が、読んで作る側）")
save(fig, "a445_dependency_graph.png", SRC)
# 図2：流し方ごとの、古い数字が残る割合と枚数
fig, axs = plt.subplots(1, 2, figsize=(11, 4.4), sharey=True); y = np.arange(len(S))[::-1]
axs[0].barh(y, S.any_stale, color=BLUE); axs[0].set_yticks(y); axs[0].set_yticklabels(S.case, fontsize=9); axs[0].set_xlabel("古い数字の表が1枚でも残った回の割合（%）")
for yy, v in zip(y, S.any_stale): axs[0].text(v + 1, yy, f"{v:.0f}%", va="center", fontsize=9)
axs[1].barh(y, S.stale_mean_when_any, color=ORANGE); axs[1].set_xlabel("残った回の、古い数字の表の枚数（平均、20枚のうち）")
for yy, v in zip(y, S.stale_mean_when_any): axs[1].text(v + 0.1, yy, f"{v:.1f}", va="center", fontsize=9)
fig.suptitle("流し方ごとの結果（所要時間を毎回ゆらして1,000回）", fontsize=13)
save(fig, "a445_stale_by_case.png", SRC)
# 図3：検査で見つかった割合
fig, ax = plt.subplots(figsize=(10, 4.4)); ss = S[S.any_stale > 0]; x = np.arange(len(ss)); w = 0.27
ax.bar(x - w, ss.found_finish, w, color=LIGHT, label="できあがりの時刻を比べる"); ax.bar(x, ss.found_start, w, color=BLUE, label="読みはじめの時刻も記録して比べる"); ax.bar(x + w, ss.found_date, w, color=INK, label="元データの日付を比べる")
ax.set_xticks(x); ax.set_xticklabels([c.replace("（", "\n（").replace("2枚が", "2枚が\n").replace("、", "、\n") for c in ss.case], fontsize=8); ax.set_ylabel("原因の表をすべて見つけた回の割合（%）"); ax.set_ylim(0, 108)
ax.set_title("流したあとの検査で、順番の誤りが見つかる割合", pad=30); ax.legend(frameon=False, fontsize=8.5, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3)
save(fig, "a445_checks.png", SRC)
print(S.round(2).to_string()); print(SW.to_string()); print(json.dumps(main["late"], ensure_ascii=False)); print(json.dumps(main["adjacent"], ensure_ascii=False))
