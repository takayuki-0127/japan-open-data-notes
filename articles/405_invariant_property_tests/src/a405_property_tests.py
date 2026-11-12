"""405 「合計は変わらない」「件数は減らない」という決まりだけで、処理の誤りはどこまで見つかるか
架空のデータ処理（つなぐ・絞る・集計・按分・出力の5段、pipeline.py）に誤りを20個入れ、
①入力を乱数で作って「決まり」を確かめる試験（性質にもとづくテスト）と、②期待する答えを1件ずつ書く試験を比べる。"""
import json, random
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT
from pipeline import run, BUGS

SEED = 405
SRC = "架空のデータ処理と架空の入力（作成者が乱数で作成、seed 405）"
TRIALS = 300
REG = ["北", "東", "中", "西", "南", "海外", "島", "山"]
DEP = ["食品", "飲料", "日用品", "衣料", "家電", "雑貨", "書籍", "玩具", "園芸", "文具"]


def gen(rng, edge=True):
    """入力を1つ作る。edge=True は端の入力（マスタにない顧客・空の状態・大文字・返品・重複・空白つきのキー・全部0）も混ぜる"""
    nc = rng.randint(1, 30)
    custs = [f"C{i:03d}" for i in range(nc)]
    master = []
    for c in custs:
        if edge and rng.random() < .10: continue                       # マスタにない顧客
        r = rng.choice(REG[: rng.randint(1, 8)])
        if edge and rng.random() < .05: r = None                       # 地域が空
        master.append((c + (" " if edge and rng.random() < .05 else ""), r))
        if edge and rng.random() < .05: master.append((c, rng.choice(REG)))   # 同じ顧客がもう1行
    n = rng.choice([0, 1, 2, 5, 20, 80, 300]) if edge else rng.choice([5, 20, 80])
    allzero = edge and rng.random() < .03
    deps = DEP[: rng.randint(1, 10)]
    orders = []
    for i in range(n):
        if edge:
            st = rng.choices(["done", "cancel", "CANCEL", None], [.80, .10, .05, .05])[0]
            a = 0 if allzero else rng.choices([rng.randint(1, 50000), -rng.randint(1, 20000), 0], [.92, .05, .03])[0]
        else:
            st = rng.choices(["done", "cancel"], [.9, .1])[0]; a = rng.randint(1, 50000)
        orders.append((i, rng.choice(custs), rng.choice(deps), a, st))
    cost = rng.choice([0, 1, 7, 100, 9999, 100000, 1234567]) if edge else rng.choice([100000, 1234567])
    return orders, master, cost


def live(orders): return [o for o in orders if (o[4] or "").lower() != "cancel"]


def unknown_n(orders, master):
    m = {}
    for c, r in master: m.setdefault(c.strip(), r)
    return sum(1 for o in live(orders) if m.get(o[1].strip()) is None)


PROPS = ["P1 件数が合う", "P2 金額の合計が変わらない", "P3 按分の合計が費用と同じ", "P4 按分は0以上で、金額の大きい区分ほど少なくない",
         "P5 利益＝金額−費用", "P6 入力の並びを変えても同じ", "P7 金額を2倍にすると金額だけ2倍", "P8 キーが重ならない", "P9 2つに分けて流して足すと同じ"]
EXTRA = "P10 「不明」の件数＝マスタにない顧客の注文の件数"


def check(orders, master, cost, bug, rng):
    """決まりを確かめる。破れた決まりの名前の集合を返す（例外で落ちたら 'crash'）"""
    bad = set()
    try:
        out = run(orders, master, cost, bug)
        lv = live(orders)
        if sum(r[2] for r in out) != len(lv): bad.add(PROPS[0])
        if sum(r[3] for r in out) != sum(o[3] for o in lv): bad.add(PROPS[1])
        if out and sum(r[4] for r in out) != cost: bad.add(PROPS[2])
        pos = sorted([(r[3], r[4]) for r in out if r[3] > 0])
        if any(r[4] < 0 for r in out) or any(pos[i][0] < pos[i + 1][0] and pos[i][1] > pos[i + 1][1] for i in range(len(pos) - 1)) \
           or any(r[4] != 0 for r in out if r[3] < 0 and any(x[3] > 0 for x in out)): bad.add(PROPS[3])
        if any(r[5] != r[3] - r[4] for r in out): bad.add(PROPS[4])
        sh = orders[:]; rng.shuffle(sh)
        if run(sh, master, cost, bug) != out: bad.add(PROPS[5])
        dbl = run([(o[0], o[1], o[2], o[3] * 2, o[4]) for o in orders], master, cost, bug)
        if [(r[0], r[1], r[2], r[3], r[4]) for r in dbl] != [(r[0], r[1], r[2], r[3] * 2, r[4]) for r in out]: bad.add(PROPS[6])
        if len({(r[0], r[1]) for r in out}) != len(out): bad.add(PROPS[7])
        h = len(orders) // 2; tot = {}
        for part in (orders[:h], orders[h:]):
            for r in run(part, master, 0, bug):
                t = tot.setdefault((r[0], r[1]), [0, 0]); t[0] += r[2]; t[1] += r[3]
        if sorted((k[0], k[1], v[0], v[1]) for k, v in tot.items()) != [(r[0], r[1], r[2], r[3]) for r in out]: bad.add(PROPS[8])
        if sum(r[2] for r in out if r[0] == "不明") != unknown_n(orders, master): bad.add(EXTRA)
    except Exception:
        bad.add("crash")
    return bad


# 正しい処理は、どの入力でも決まりを破らない
rng = random.Random(SEED)
for _ in range(2000):
    o, m, c = gen(rng, True)
    assert not check(o, m, c, None, rng), "正しい処理が決まりを破った"

# ---------------- ① 決まりを確かめる試験 ----------------
rows, hit = [], {}
for edge in (True, False):
    rng = random.Random(SEED + (1 if edge else 2))
    inputs = [gen(rng, edge) for _ in range(TRIALS)]
    for b in BUGS:
        r2 = random.Random(SEED)
        first, n_hit, props, n_hit10, first10 = None, 0, {}, 0, None
        for i, (o, m, c) in enumerate(inputs):
            bad = check(o, m, c, b, r2)
            gen_bad = bad - {EXTRA}
            if gen_bad:
                n_hit += 1; first = i + 1 if first is None else first
                for p in gen_bad: props[p] = props.get(p, 0) + 1
            if bad:
                n_hit10 += 1; first10 = i + 1 if first10 is None else first10
        rows.append({"誤り": b, "段": BUGS[b][0], "内容": BUGS[b][1], "入力": "端の入力も混ぜる" if edge else "ふつうの入力だけ",
                     "見つけた": int(first is not None), "最初に見つけた回": first, "1回で見つかる割合": n_hit / TRIALS,
                     "破れた決まり": "・".join(sorted(p.split(" ")[0] for p in props)), "P10も足して見つけた": int(first10 is not None),
                     "P10も足して1回で見つかる割合": n_hit10 / TRIALS})
        hit[(b, edge)] = props
prop = pd.DataFrame(rows); prop.to_csv(RES / "property_tests.csv", index=False)

# ---------------- ② 期待する答えを1件ずつ書く試験 ----------------
M0 = [("C001", "東"), ("C002", "東"), ("C003", "西"), ("C004", "西")]
def O(*xs): return [(i, c, d, a, s) for i, (c, d, a, s) in enumerate(xs)]
PLAIN = {  # ふつうの3件：端の入力なし
 "E1 2地域×2部門": (O(("C001", "食品", 1200, "done"), ("C002", "食品", 800, "done"), ("C003", "家電", 30000, "done"), ("C004", "食品", 500, "done")), M0, 1000),
 "E2 取消が1件": (O(("C001", "食品", 1200, "done"), ("C001", "家電", 9800, "cancel"), ("C003", "家電", 30000, "done")), M0, 5000),
 "E3 同じ区分に複数行": (O(("C001", "食品", 100, "done"), ("C001", "食品", 200, "done"), ("C002", "食品", 300, "done"), ("C003", "食品", 400, "done")), M0, 999),
}
EDGE = {   # 端の入力を1つずつ足した8件（合わせて11件）
 "E4 マスタにない顧客": (O(("C001", "食品", 1200, "done"), ("C999", "食品", 700, "done")), M0, 1000),
 "E5 状態が空": (O(("C001", "食品", 1200, None), ("C003", "食品", 700, "done")), M0, 1000),
 "E6 大文字の CANCEL": (O(("C001", "食品", 1200, "CANCEL"), ("C003", "食品", 700, "done")), M0, 1000),
 "E7 返品（マイナス）": (O(("C001", "食品", 1200, "done"), ("C001", "家電", -5000, "done"), ("C003", "食品", 700, "done")), M0, 1000),
 "E8 マスタの重複": (O(("C001", "食品", 1200, "done"), ("C003", "食品", 700, "done")), M0 + [("C001", "西")], 1000),
 "E9 キーの後ろに空白": (O(("C001", "食品", 1200, "done"), ("C003", "食品", 700, "done")), [("C001 ", "東"), ("C003", "西")], 1000),
 "E10 金額が全部0": (O(("C001", "食品", 0, "done"), ("C003", "食品", 0, "done")), M0, 1000),
 "E11 地域が空の顧客": (O(("C001", "食品", 1200, "done"), ("C003", "食品", 700, "done")), [("C001", None), ("C003", "西")], 1000),
}
ex = []
for b in BUGS:
    def caught(cases):
        out = []
        for name, (o, m, c) in cases.items():
            try:
                if run(o, m, c, b) != run(o, m, c, None): out.append(name.split(" ")[0])
            except Exception: out.append(name.split(" ")[0])
        return out
    p, e = caught(PLAIN), caught(EDGE)
    ex.append({"誤り": b, "ふつうの3件で見つけた": int(bool(p)), "11件で見つけた": int(bool(p or e)), "見つけた例": "・".join(p + e)})
ex = pd.DataFrame(ex); ex.to_csv(RES / "example_tests.csv", index=False)
golden = {k: run(*v) for k, v in {**PLAIN, **EDGE}.items()}
json.dump({k: {"入力": {"orders": v[0], "master": v[1], "cost": v[2]}, "期待する答え": golden[k]} for k, v in {**PLAIN, **EDGE}.items()},
          open(DATA / "example_cases.json", "w"), ensure_ascii=False, indent=1)

# ---------------- まとめ ----------------
pe, pp = prop[prop["入力"] == "端の入力も混ぜる"].set_index("誤り"), prop[prop["入力"] == "ふつうの入力だけ"].set_index("誤り")
exi = ex.set_index("誤り")
tab = pd.DataFrame({"誤り": list(BUGS), "段": [BUGS[b][0] for b in BUGS], "内容": [BUGS[b][1] for b in BUGS],
                    "決まり9つ・ふつうの入力": pp["見つけた"].values, "決まり9つ・端も混ぜる": pe["見つけた"].values,
                    "決まり10・端も混ぜる": pe["P10も足して見つけた"].values, "例3件": exi["ふつうの3件で見つけた"].values, "例11件": exi["11件で見つけた"].values,
                    "破れた決まり": pe["破れた決まり"].values, "最初に見つけた回": pe["最初に見つけた回"].values, "1回で見つかる割合": pe["1回で見つかる割合"].values})
tab["決まり9つ＋例3件"] = ((tab["決まり9つ・端も混ぜる"] + tab["例3件"]) > 0).astype(int)
tab["決まり9つ＋例11件"] = ((tab["決まり9つ・端も混ぜる"] + tab["例11件"]) > 0).astype(int)
tab.to_csv(RES / "bugs_table.csv", index=False)
cnt = {c: int(tab[c].sum()) for c in ["例3件", "例11件", "決まり9つ・ふつうの入力", "決まり9つ・端も混ぜる", "決まり10・端も混ぜる", "決まり9つ＋例3件", "決まり9つ＋例11件"]}

# 乱数の種を変えた20回：端も混ぜる入力300回で見つけた数
rep = []
for sd in range(20):
    rng = random.Random(9000 + sd); inputs = [gen(rng, True) for _ in range(TRIALS)]
    for n_try in (10, 30, 100, 300):
        f = 0
        for b in BUGS:
            r2 = random.Random(sd)
            if any(check(o, m, c, b, r2) - {EXTRA} for o, m, c in inputs[:n_try]): f += 1
        rep.append({"seed": 9000 + sd, "試した入力の数": n_try, "見つけた数": f})
rep = pd.DataFrame(rep); rep.to_csv(RES / "repeat20.csv", index=False)
rs = rep.groupby("試した入力の数")["見つけた数"].agg(["median", "min", "max"]).reset_index(); rs.to_csv(RES / "repeat20_summary.csv", index=False)

# 決まりごとに、単独でいくつ見つけるか
solo = {p: sum(1 for b in BUGS if p in hit[(b, True)]) for p in PROPS}
json.dump({"誤りの数": len(BUGS), "1つの入力の組": TRIALS, "見つけた数": cnt, "決まり1つだけで見つけた数": solo,
           "決まり9つで見つからなかった誤り": tab.loc[tab["決まり9つ・端も混ぜる"] == 0, "誤り"].tolist(),
           "例11件で見つからなかった誤り": tab.loc[tab["例11件"] == 0, "誤り"].tolist(),
           "20回のくり返し": rs.to_dict("records")}, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

# ---------------- 図 ----------------
fig, ax = plt.subplots(figsize=(8.6, 4.2)); ks = list(cnt); y = np.arange(len(ks))
ax.barh(y, [cnt[k] for k in ks], color=[GRAY, GRAY, LIGHT, BLUE, BLUE, GREEN, GREEN])
for i, k in enumerate(ks): ax.text(cnt[k] + .2, i, f"{cnt[k]} / 20", va="center", fontsize=10)
ax.set_yticks(y); ax.set_yticklabels(["期待する答えを書いた例3件（ふつうの入力）", "期待する答えを書いた例11件（端の入力も）", "決まり9つ（ふつうの入力だけ300回）", "決まり9つ（端の入力も混ぜて300回）",
                                      "決まり9つ＋この処理だけの決まり1つ", "決まり9つ＋例3件", "決まり9つ＋例11件"], fontsize=9); ax.invert_yaxis()
ax.set_xlim(0, 23); ax.set_xlabel("入れた誤り20個のうち、見つけた数"); ax.set_title("試験の種類ごとの、見つけた誤りの数")
save(fig, "a405_found_by_method.png", SRC)

fig, ax = plt.subplots(figsize=(9.6, 6.4))
M = np.array([[1 if p.split(" ")[0] in tab["破れた決まり"][i].split("・") else 0 for p in PROPS] for i in range(len(tab))])
ax.imshow(M, cmap="Blues", vmin=0, vmax=1.6, aspect="auto")
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        if M[i, j]: ax.text(j, i, "●", ha="center", va="center", fontsize=9, color="white")
ax.set_xticks(range(len(PROPS))); ax.set_xticklabels([p.split(" ")[0] for p in PROPS], fontsize=10); ax.xaxis.tick_top()
ax.set_yticks(range(len(tab))); ax.set_yticklabels([f"{b}（{BUGS[b][0]}）{BUGS[b][1][:22]}" for b in BUGS], fontsize=8)
for i in range(len(tab)):
    if tab["決まり9つ・端も混ぜる"][i] == 0: ax.get_yticklabels()[i].set_color(ORANGE)
for s in ax.spines.values(): s.set_visible(False)
ax.set_title("どの誤りが、どの決まりを破ったか（端の入力も混ぜた300回）", pad=40, fontsize=12)
save(fig, "a405_bug_by_property.png", SRC + "。橙の行は、決まり9つのどれも破らなかった誤り", y=0.0)

fig, ax = plt.subplots(figsize=(8.6, 5.2)); d = tab.sort_values("1回で見つかる割合", ascending=True).reset_index(drop=True); y = np.arange(len(d))
ax.barh(y, d["1回で見つかる割合"] * 100, color=[ORANGE if v == 0 else BLUE for v in d["1回で見つかる割合"]])
for i in range(len(d)): ax.text(d["1回で見つかる割合"][i] * 100 + 1, i, f"{d['1回で見つかる割合'][i]:.0%}" if d["1回で見つかる割合"][i] > 0 else "0%（見つからない）", va="center", fontsize=8)
ax.set_yticks(y); ax.set_yticklabels([f"{b} {BUGS[b][1][:20]}" for b in d["誤り"]], fontsize=8); ax.set_xlim(0, 112)
ax.set_xlabel("入力1つあたり、決まり9つのどれかが破れた割合（%）"); ax.set_title("誤りごとの、入力1つで見つかる割合")
save(fig, "a405_hit_rate_per_input.png", SRC + "。端の入力も混ぜた300回")
pd.set_option("display.width", 250); print(tab.drop(columns=["内容"]).to_string()); print(cnt); print(solo); print(rs.to_string()); print(ex.to_string())
