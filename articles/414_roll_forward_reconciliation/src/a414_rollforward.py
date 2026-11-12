"""414 「期首＋増加−減少＝期末」の照合は、どんな誤りを見つけ、何を見逃すのか
架空の契約の異動の記録（新規・解約・満期・復活・中途変更）24か月分に、誤りを10種類入れて照合する。乱数の種は414。"""
import json
from collections import Counter, defaultdict
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(414)
M = 24
TR = 200                                            # 誤り1種類あたりの試行の数


def prem(n):
    return (np.round(np.exp(rng.normal(np.log(6000), 0.45, n)) / 100) * 100).astype(int)


# ---------------- 正しい記録を作る ----------------
snap = [dict(zip(range(1, 20001), prem(20000).tolist()))]        # snap[m]：m 月末に有効な契約 {契約ID: 月の保険料}
events = [[]]                                                     # events[m]：m 月の異動 (契約ID, 種類, 金額)
lapsed = {}                                                       # 解約した契約 {契約ID: (解約月, 保険料)}
next_id = 20001
for m in range(1, M + 1):
    cur = dict(snap[m - 1]); ev = []
    ids = np.array(list(cur)); u = rng.random(len(ids))
    for i in ids[u < 0.012].tolist():                             # 解約
        ev.append((i, "解約", cur[i])); lapsed[i] = (m, cur.pop(i))
    for i in ids[(u >= 0.012) & (u < 0.015)].tolist():            # 満期
        ev.append((i, "満期", cur.pop(i)))
    stay = ids[u >= 0.015]
    for i in stay[rng.random(len(stay)) < 0.02].tolist():         # 中途変更（保険料の増減）
        d = int(rng.choice([-1, 1]) * rng.integers(1, 21) * 100)
        if cur[i] + d < 500: d = abs(d)
        ev.append((i, "中途変更", d)); cur[i] += d
    for i, (lm, p) in list(lapsed.items()):                       # 復活（解約から3か月以内）
        if lm == m: continue
        if m - lm > 3: del lapsed[i]; continue
        if rng.random() < 0.08:
            ev.append((i, "復活", p)); cur[i] = p; del lapsed[i]
    for p in prem(rng.poisson(450)).tolist():                     # 新規
        ev.append((next_id, "新規", p)); cur[next_id] = p; next_id += 1
    snap.append(cur); events.append(ev)

E = pd.DataFrame([(m, i, t, a) for m in range(1, M + 1) for (i, t, a) in events[m]], columns=["月", "契約ID", "種類", "金額"])
S = pd.DataFrame([(m, i, p) for m in range(M + 1) for i, p in snap[m].items()], columns=["月", "契約ID", "保険料"])
E.to_csv(DATA / "movements.csv", index=False)
S[S["月"].isin([0, 1, 2, 12, 24])].to_csv(DATA / "snapshots_sample_months.csv", index=False)   # 一覧は大きいので、一部の月だけ置く

SIGN = {"新規": 1, "復活": 1, "解約": -1, "満期": -1}


def check_month(bom, eom, ev):
    """1か月分の3つの照合。返り値は (件数の照合が合わない, 保険料の照合が合わない, 契約ごとの照合が合わない)"""
    dn = sum(SIGN.get(t, 0) for _, t, _ in ev)
    dp = sum(SIGN[t] * a if t in SIGN else a for _, t, a in ev)
    c1 = len(bom) + dn != len(eom)
    c2 = sum(bom.values()) + dp != sum(eom.values())
    cnt = Counter(); amt = defaultdict(int)                       # 契約ごとの、件数と保険料の増減
    for i, t, a in ev:
        if t in SIGN: cnt[i] += SIGN[t]; amt[i] += SIGN[t] * a
        else: amt[i] += a
    c3 = False
    for i in set(cnt) | set(amt) | (set(bom) ^ set(eom)):
        if (i in bom) + cnt[i] != (i in eom) or bom.get(i, 0) + amt[i] != eom.get(i, 0):
            c3 = True; break
    if not c3:                                                    # 異動のない契約の保険料が、月末の一覧で変わっていないか
        for i in eom.keys() - set(cnt) - set(amt):
            if eom[i] != bom.get(i): c3 = True; break
    return c1, c2, c3


clean = [check_month(snap[m - 1], snap[m], events[m]) for m in range(1, M + 1)]
assert not any(any(c) for c in clean), "正しい記録は、すべての月・すべての照合で合う"


def pick(ev, kind, r):
    idx = [k for k, e in enumerate(ev) if e[1] == kind]
    return idx[r.integers(len(idx))]


def inject(name, m, r):
    """誤りを1つ入れた (snap, events) の、関係する月だけを返す：{月: (期首, 期末, 異動)}"""
    ev = list(events[m]); ev2 = list(events[m + 1]); eom = snap[m]
    if name == "E1 解約の記録が1件抜ける":
        del ev[pick(ev, "解約", r)]
    elif name == "E2 新規の記録が二重に入る":
        ev.append(ev[pick(ev, "新規", r)])
    elif name == "E3 新規の記録が翌月にずれる":
        ev2.append(ev.pop(pick(ev, "新規", r)))
    elif name == "E4 解約を満期と書く":
        k = pick(ev, "解約", r); ev[k] = (ev[k][0], "満期", ev[k][2])
    elif name == "E5 同じ月に解約1件と新規1件の記録が抜ける":
        del ev[pick(ev, "解約", r)]; del ev[pick(ev, "新規", r)]
    elif name == "E6 中途変更の増減の符号が逆":
        k = pick(ev, "中途変更", r); ev[k] = (ev[k][0], "中途変更", -ev[k][2])
    elif name == "E7 中途変更の記録が1件抜ける":
        del ev[pick(ev, "中途変更", r)]
    elif name == "E8 復活を新規と書く":
        k = pick(ev, "復活", r); ev[k] = (ev[k][0], "新規", ev[k][2])
    elif name == "E9 解約した契約が月末の一覧に残る":
        k = pick(ev, "解約", r); eom = dict(eom); eom[ev[k][0]] = ev[k][2]
    elif name == "E10 月末の一覧で2件の保険料が入れ替わる":
        ids = list(eom); a, b = (ids[k] for k in r.choice(len(ids), 2, replace=False))
        eom = dict(eom); eom[a], eom[b] = eom[b], eom[a]
    return {m: (snap[m - 1], eom, ev), m + 1: (eom, snap[m + 1], ev2)}


ERR = ["E1 解約の記録が1件抜ける", "E2 新規の記録が二重に入る", "E3 新規の記録が翌月にずれる", "E4 解約を満期と書く",
       "E5 同じ月に解約1件と新規1件の記録が抜ける", "E6 中途変更の増減の符号が逆", "E7 中途変更の記録が1件抜ける",
       "E8 復活を新規と書く", "E9 解約した契約が月末の一覧に残る", "E10 月末の一覧で2件の保険料が入れ替わる"]
rows = []
for name in ERR:
    r = np.random.default_rng(4140 + ERR.index(name))
    f1 = f2 = f3 = both = months_c1 = 0
    for _ in range(TR):
        m = int(r.integers(2, M))                                 # 2〜23か月目のどこかに入れる
        res = [check_month(*v) for v in inject(name, m, r).values()]
        a, b, c = (any(x[k] for x in res) for k in range(3))
        f1 += a; f2 += b; f3 += c; both += (a or b); months_c1 += sum(x[0] for x in res)
    rows.append({"誤り": name, "件数の照合で見つかった%": 100 * f1 / TR, "保険料の照合で見つかった%": 100 * f2 / TR,
                 "件数か保険料のどちらかで見つかった%": 100 * both / TR, "契約ごとの照合で見つかった%": 100 * f3 / TR,
                 "件数の照合が合わなかった月の数（平均）": round(months_c1 / TR, 2)})
T = pd.DataFrame(rows); T.to_csv(RES / "detection_by_error.csv", index=False)
found = {c: int((T[c] >= 99.9).sum()) for c in T.columns if c.endswith("%")}
partly = {c: int(((T[c] > 0) & (T[c] < 99.9)).sum()) for c in T.columns if c.endswith("%")}

# ---------------- 月ごとの増減の表（正しい記録）と、SQL（DuckDB）での照合 ----------------
db = duckdb.connect(); db.execute("SET threads=1"); db.register("e", E); db.register("s", S)
RF = db.execute("""
WITH mv AS (
  SELECT 月,
         SUM(CASE WHEN 種類 = '新規' THEN 1 ELSE 0 END) AS 新規, SUM(CASE WHEN 種類 = '復活' THEN 1 ELSE 0 END) AS 復活,
         SUM(CASE WHEN 種類 = '解約' THEN 1 ELSE 0 END) AS 解約, SUM(CASE WHEN 種類 = '満期' THEN 1 ELSE 0 END) AS 満期,
         SUM(CASE WHEN 種類 IN ('新規', '復活') THEN 金額 WHEN 種類 IN ('解約', '満期') THEN -金額 ELSE 金額 END) AS 保険料の増減
  FROM e GROUP BY 月),
st AS (SELECT 月, COUNT(*) AS 件数, SUM(保険料) AS 保険料 FROM s GROUP BY 月)
SELECT mv.月, b.件数 AS 期首の件数, mv.新規, mv.復活, mv.解約, mv.満期, t.件数 AS 期末の件数,
       b.件数 + mv.新規 + mv.復活 - mv.解約 - mv.満期 - t.件数 AS 件数の差,
       b.保険料 AS 期首の保険料, mv.保険料の増減, t.保険料 AS 期末の保険料,
       b.保険料 + mv.保険料の増減 - t.保険料 AS 保険料の差
FROM mv JOIN st b ON b.月 = mv.月 - 1 JOIN st t ON t.月 = mv.月 ORDER BY mv.月""").df()
assert (RF["件数の差"] == 0).all() and (RF["保険料の差"] == 0).all()
RF.to_csv(RES / "roll_forward_clean.csv", index=False)

# 例：E5（同じ月に解約1件と新規1件が抜ける）を12か月目に入れたとき
r = np.random.default_rng(41400)
ex = inject("E5 同じ月に解約1件と新規1件の記録が抜ける", 12, r)[12]
bom, eom, ev = ex
exm = {"月": 12, "期首の件数": len(bom), "期末の件数": len(eom),
       "新規": sum(t == "新規" for _, t, _ in ev), "復活": sum(t == "復活" for _, t, _ in ev),
       "解約": sum(t == "解約" for _, t, _ in ev), "満期": sum(t == "満期" for _, t, _ in ev)}
exm["件数の差"] = exm["期首の件数"] + exm["新規"] + exm["復活"] - exm["解約"] - exm["満期"] - exm["期末の件数"]
exm["保険料の差"] = int(sum(bom.values()) + sum(SIGN[t] * a if t in SIGN else a for _, t, a in ev) - sum(eom.values()))
exm["照合"] = [bool(x) for x in check_month(bom, eom, ev)]

main = {"月の数": M, "契約の数（期首）": len(snap[0]), "契約の数（24か月目の月末）": len(snap[M]), "異動の記録の数": int(len(E)),
        "異動の種類ごとの数": E["種類"].value_counts().to_dict(), "誤り1種類あたりの試行": TR,
        "正しい記録で合わなかった月": 0, "誤りごとの結果": T.to_dict("records"),
        "10種類のうち、必ず見つかった誤りの数": found, "10種類のうち、一部の試行だけ見つかった誤りの数": partly,
        "例_E5を12か月目に入れる": exm}
json.dump(main, open(RES / "a414_main.json", "w"), ensure_ascii=False, indent=1, default=int)

# ---------------- 図 ----------------
SRC = "架空の契約の異動の記録24か月分（作成者が乱数で作成、seed 414）"
cols = ["件数の照合で見つかった%", "保険料の照合で見つかった%", "契約ごとの照合で見つかった%"]
fig, ax = plt.subplots(figsize=(10, 5))
Z = T[cols].to_numpy()
ax.imshow(Z, cmap="Blues", vmin=0, vmax=140, aspect="auto")
ax.set_xticks(range(3)); ax.set_xticklabels(["件数の照合", "保険料の照合", "契約ごとの照合"]); ax.xaxis.tick_top()
ax.set_yticks(range(len(T))); ax.set_yticklabels(T["誤り"])
for i in range(Z.shape[0]):
    for j in range(Z.shape[1]):
        ax.text(j, i, f"{Z[i, j]:.0f}%", ha="center", va="center", color="white" if Z[i, j] > 70 else INK)
for s_ in ax.spines.values(): s_.set_visible(False)
ax.tick_params(length=0); ax.set_title("誤りを200回ずつ入れて、見つかった割合", pad=28)
save(fig, "a414_detection_table.png", SRC)

fig, ax = plt.subplots(figsize=(9, 4.2))
lab = ["件数の照合だけ", "件数＋保険料の照合", "契約ごとの照合"]
v = [found["件数の照合で見つかった%"], found["件数か保険料のどちらかで見つかった%"], found["契約ごとの照合で見つかった%"]]
pv = [partly["件数の照合で見つかった%"], partly["件数か保険料のどちらかで見つかった%"], partly["契約ごとの照合で見つかった%"]]
b = ax.bar(lab, v, color=[GRAY, BLUE, GREEN], label="必ず見つかった")
ax.bar(lab, pv, bottom=v, color=LIGHT, label="一部の試行だけ見つかった")
for r_, y, q in zip(b, v, pv): ax.text(r_.get_x() + r_.get_width() / 2, y + q, f"{y}種類" + (f"（＋一部{q}）" if q else ""), ha="center", va="bottom")
ax.set_ylim(0, 11); ax.set_ylabel("10種類のうち、見つかった誤りの種類"); ax.set_title("照合の細かさと、見つかる誤りの種類"); ax.legend(frameon=False, loc="upper left")
save(fig, "a414_found_types.png", SRC)

fig, ax = plt.subplots(figsize=(9.5, 4.2))
r12 = RF[RF["月"] == 12].iloc[0]
steps = [("期首", r12["期首の件数"]), ("＋新規", r12["新規"]), ("＋復活", r12["復活"]), ("−解約", -r12["解約"]), ("−満期", -r12["満期"])]
lvl = 0; base0 = r12["期首の件数"] - 900
for k, (n_, d) in enumerate(steps):
    if k == 0: ax.bar(n_, d - base0, bottom=base0, color=GRAY); lvl = d; ax.text(k, d, f"{int(d):,}", ha="center", va="bottom")
    else:
        ax.bar(n_, abs(d), bottom=min(lvl, lvl + d), color=BLUE if d > 0 else ORANGE); lvl += d
        ax.text(k, max(lvl, lvl - d), f"{int(d):+,}", ha="center", va="bottom")
ax.bar("期末", r12["期末の件数"] - base0, bottom=base0, color=GRAY); ax.text(5, r12["期末の件数"], f"{int(r12['期末の件数']):,}", ha="center", va="bottom")
ax.set_ylim(base0, max(r12["期首の件数"], r12["期末の件数"]) + 700); ax.set_ylabel("件数")
ax.set_title("12か月目の増減：期首＋新規＋復活−解約−満期＝期末（正しい記録）")
save(fig, "a414_roll_forward_month12.png", SRC)
print(T.to_string()); print(found, partly); print(exm); print(main["異動の種類ごとの数"])
