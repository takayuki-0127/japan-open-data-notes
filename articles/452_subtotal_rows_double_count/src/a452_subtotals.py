"""452 小計や合計の行が混ざった表をそのまま足すと、合計は何倍になるのか
消費者物価指数（2020年基準）のウエイトの表（総合・類・品目が1列に並ぶ）で確かめる。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import DATA, RES, BLUE, ORANGE, GRAY, GREEN, LIGHT, save

m = pd.read_csv(DATA / "cpi2020_weights.csv", dtype={"code": str})
m["is_item"] = ~m.code.str.startswith("0")                    # 品目（いちばん細かい行）
first_bekkei = m.index[m.name == "生鮮食品"][0]               # ここから後ろは「別掲」（組み替えた合計・再掲）
m["bekkei"] = m.index >= first_bekkei
TOTAL = m.weight.iloc[0]
m["w10000"] = m.weight / TOTAL * 10000                        # 総合＝10,000 とする割合


# ---------- 本当の階層（品目の和で親を決める） ----------
def parse_truth(df):
    """行の並びと値から、各行の深さと親を決める。正しい値（丸めなし）で、親＝子の和になる所まで子を取る。"""
    v = df.weight.values; n = len(df)
    depth = np.zeros(n, int); parent = np.full(n, -1)

    def walk(i, d, p):
        depth[i] = d; parent[i] = p
        if df.is_item.values[i]:
            return i + 1
        j = i + 1; s = 0.0
        while j < n and s < v[i] * (1 - 1e-12):
            s += v[j]
            j = walk(j, d + 1, i)
        assert abs(s - v[i]) <= 1e-6 * v[i], (df.name.values[i], s, v[i])
        return j
    end = walk(0, 0, -1)
    return depth, parent, end


main = m[~m.bekkei].reset_index(drop=True)
depth, parent, end = parse_truth(main)
assert end == len(main)
main["depth"] = depth; main["parent"] = parent
main["top"] = ""
for i in range(len(main)):                                     # 10大費目の名前
    j = i
    while main.depth[j] > 1:
        j = main.parent[j]
    main.loc[i, "top"] = main.name[j] if main.depth[j] == 1 else "総合"
main[["name", "code", "weight", "w10000", "is_item", "depth", "parent", "top"]].to_csv(DATA / "cpi2020_weights_with_levels.csv", index=False)

# ---------- そのまま足すと何倍か ----------
ratio_all = m.weight.sum() / TOTAL                             # 別掲も含めて全部
ratio_main = main.weight.sum() / TOTAL                         # 別掲を除く
by_depth = main.groupby("depth").agg(rows=("weight", "size"), items=("is_item", "sum"), weight=("weight", "sum")).reset_index()
by_depth["share_of_total"] = by_depth.weight / TOTAL
by_depth.to_csv(RES / "rows_by_depth.csv", index=False)
bytop = []
for t, g in main[main.depth >= 1].groupby("top", sort=False):
    true = g[g.is_item].weight.sum()
    bytop.append({"top": t, "rows": len(g), "items": int(g.is_item.sum()), "subtotal_rows": int((~g.is_item).sum()),
                  "max_depth": int(g.depth.max()), "naive_ratio": round(g.weight.sum() / true, 3)})
bytop = pd.DataFrame(bytop); bytop.to_csv(RES / "naive_ratio_by_group.csv", index=False)
# 品目から見た、上にある小計の行の数（＝そのまま足すと何回数えられるか）
main["times_counted"] = main.depth + 1
cnt = main[main.is_item].groupby("times_counted").agg(items=("weight", "size"), weight=("weight", "sum")).reset_index()
cnt["weight_share"] = cnt.weight / TOTAL
cnt.to_csv(RES / "times_counted.csv", index=False)

# ---------- DuckDB：そのまま SUM、品目だけ SUM ----------
con = duckdb.connect(); con.register("t", m[["name", "code", "weight", "is_item", "bekkei"]])
q = con.execute("""
SELECT SUM(weight) AS naive_all,
       SUM(CASE WHEN NOT bekkei THEN weight END) AS naive_without_bekkei,
       SUM(CASE WHEN is_item THEN weight END) AS items_only,
       MAX(CASE WHEN code = '0001' THEN weight END) AS total_row
FROM t""").df()
q["ratio_all"] = q.naive_all / q.total_row; q["ratio_main"] = q.naive_without_bekkei / q.total_row; q["ratio_items"] = q.items_only / q.total_row
q.to_csv(RES / "sql_check_duckdb.csv", index=False)
assert abs(q.ratio_items[0] - 1) < 1e-9 and abs(q.ratio_all[0] - ratio_all) < 1e-9

# ---------- 小計の行を機械で見つける決まり ----------
truth_sub = ~main.is_item.values


def detect(vals, tol_fn, min_k=2):
    """親＝子の和の決まり。各行について、後ろに続く行（子はさらに自分の子を持てる）を足して自分の値に届けば小計とみなす。
    tol_fn(子の数) が許す差。min_k は、小計とみなすのに要る子の数（1 なら「直後の行と同じ値」も小計とみなす）。
    返り値：小計とみなした行の印。"""
    n = len(vals); sub = np.zeros(n, bool); memo = {}

    def walk(i):
        """i を根とするかたまりの終わりの位置を返す（結果は覚えておく）。"""
        if i in memo:
            return memo[i]
        s = 0.0; j = i + 1; k = 0
        while j < n:
            if k >= min_k and abs(s - vals[i]) <= tol_fn(k):
                break
            if s > vals[i] + tol_fn(k):
                break
            s += vals[j]; k += 1
            j = walk(j)
        if k >= min_k and abs(s - vals[i]) <= tol_fn(k):
            sub[i] = True; memo[i] = j
        else:
            memo[i] = i + 1
        return memo[i]
    for i in range(n - 1, -1, -1):                              # 後ろから埋めると、深い呼び出しにならない
        walk(i)
    # 上から順にたどって、かたまりの根だけを小計とする（途中で外れた候補は数えない）
    keep = np.zeros(n, bool)

    def mark(i):
        if not sub[i]:
            return i + 1
        keep[i] = True
        j = i + 1
        while j < memo[i]:
            j = mark(j)
        return j
    i = 0
    while i < n:
        i = mark(i)
    return keep


def score(sub):
    tp = int((sub & truth_sub).sum()); fp = int((sub & ~truth_sub).sum()); fn = int((~sub & truth_sub).sum())
    naive_after = main.weight.values[~sub].sum() / TOTAL       # 見つけた小計を除いて足した合計÷本当の合計
    return {"found": tp, "missed": fn, "false_alarm": fp, "detect_pct": round(100 * tp / truth_sub.sum(), 1), "sum_ratio_after": round(naive_after, 3)}


rules = []
EX = lambda k: 1e-6 * TOTAL / 1e4
# 名前で見つける
namehit = main.name.str.contains("計|合計|総合").values
rules.append({"rule": "名前に「計」「総合」がある行", "data": "—", **score(namehit)})
# 値で見つける：丸めなし
rules.append({"rule": "親＝子の和（子は2つ以上）", "data": "丸めなし", **score(detect(main.weight.values, EX))})
rules.append({"rule": "親＝子の和（子が1つでもよい）", "data": "丸めなし", **score(detect(main.weight.values, EX, 1))})
# 1万分比の整数に丸めた表（公表のウエイトの形）
r0 = np.round(main.w10000.values)
rules.append({"rule": "親＝子の和（子が1つでもよい、差0）", "data": "整数に丸めた表", **score(detect(r0, lambda k: 0.0, 1))})
rules.append({"rule": "親＝子の和（子が1つでもよい、差は子の数×0.5まで）", "data": "整数に丸めた表", **score(detect(r0, lambda k: 0.5 * k, 1))})
# 小数1桁に丸めた表
r1 = np.round(main.w10000.values, 1)
rules.append({"rule": "親＝子の和（子が1つでもよい、差0）", "data": "小数1桁に丸めた表", **score(detect(r1, lambda k: 1e-9, 1))})
rules.append({"rule": "親＝子の和（子が1つでもよい、差は子の数×0.05まで）", "data": "小数1桁に丸めた表", **score(detect(r1, lambda k: 0.05 * k + 1e-9, 1))})
single = int(sum((main.parent.values == i).sum() == 1 for i in np.where(truth_sub)[0]))
rules = pd.DataFrame(rules); rules.to_csv(RES / "detection_rules.csv", index=False)

# 丸めで「親＝子の和」が崩れる小計の行の割合
def broken(r):
    out = []
    for i in np.where(truth_sub)[0]:
        ch = np.where(main.parent.values == i)[0]
        out.append(abs(r[ch].sum() - r[i]) > 1e-9)
    return np.array(out)
b0, b1 = broken(r0), broken(r1)
brk = pd.DataFrame({"rounding": ["1万分比の整数", "1万分比の小数1桁"], "subtotal_rows": [len(b0), len(b1)], "broken": [int(b0.sum()), int(b1.sum())],
                    "broken_pct": [round(100 * b0.mean(), 1), round(100 * b1.mean(), 1)]})
brk.to_csv(RES / "rounding_breaks_parent_sum.csv", index=False)
zero_rows = int((r0 == 0).sum())

mainj = {"rows_all": int(len(m)), "rows_bekkei": int(m.bekkei.sum()), "rows_main": int(len(main)), "items": int(main.is_item.sum()),
         "subtotal_rows_main": int(truth_sub.sum()), "max_depth": int(main.depth.max()),
         "naive_ratio_all": round(float(ratio_all), 3), "naive_ratio_without_bekkei": round(float(ratio_main), 3),
         "bekkei_sum_ratio": round(float(m[m.bekkei].weight.sum() / TOTAL), 3),
         "rules": rules.to_dict(orient="records"), "rounding": brk.to_dict(orient="records"), "rows_rounded_to_zero": zero_rows, "single_child_subtotals": single,
         "times_counted": cnt.to_dict(orient="records")}
json.dump(mainj, open(RES / "a452_main.json", "w"), ensure_ascii=False, indent=1)

# ---------- 図 ----------
SRC = "総務省統計局「消費者物価指数」2020年基準のウエイトをもとに作成"
fig, ax = plt.subplots(figsize=(8.6, 4.4))
s = bytop.iloc[::-1]
ax.barh(s.top, s.naive_ratio, color=BLUE)
ax.axvline(1, color=GRAY, lw=1)
for i, (v, d) in enumerate(zip(s.naive_ratio, s.max_depth)):
    ax.text(v + 0.03, i, f"{v:.2f}倍（小計の段 {d - 1}）", va="center", fontsize=9)
ax.set_xlim(0, s.naive_ratio.max() * 1.3); ax.set_xlabel("そのまま足した合計 ÷ 本当の合計（品目だけの合計）")
ax.set_title("10大費目ごとの、そのまま足したときの倍率")
save(fig, "a452_naive_ratio_by_group.png", SRC)

fig, ax = plt.subplots(figsize=(8.6, 4.2))
lab = ["総合の行", "10大費目の行", "その下の類（1段目）", "その下の類（2段目）", "その下の類（3段目）", "品目の行"]
sub = main[~main.is_item].groupby("depth").weight.sum() / TOTAL
vals = [sub.get(0, 0), sub.get(1, 0), sub.get(2, 0), sub.get(3, 0), sub.get(4, 0), main[main.is_item].weight.sum() / TOTAL]
left = 0; cols = [GRAY, ORANGE, "#f1a27f", "#f6c5ae", "#fbe3d7", BLUE]
for l, v, c in zip(lab, vals, cols):
    if v <= 0:
        continue
    ax.barh(["そのまま足す"], [v], left=left, color=c, label=f"{l}（{v:.2f}）")
    left += v
ax.barh(["品目だけ足す"], [1.0], color=BLUE)
ax.set_xlabel("総合（本当の合計）を1としたときの大きさ"); ax.legend(frameon=False, fontsize=8.5, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.16))
ax.set_title(f"そのまま足すと、合計は本当の{ratio_main:.2f}倍（別掲も入れると{ratio_all:.2f}倍）")
save(fig, "a452_what_is_added.png", SRC, y=-0.12)

fig, ax = plt.subplots(figsize=(8.8, 4.4))
r = rules.iloc[::-1].reset_index(drop=True)
y = np.arange(len(r))
ax.barh(y - 0.2, r.detect_pct, 0.4, color=BLUE, label="見つけた小計の行（%）")
ax.barh(y + 0.2, 100 * r.false_alarm / main.is_item.sum(), 0.4, color=ORANGE, label="小計と間違えた品目の行（品目に対する%）")
ax.set_yticks(y); ax.set_yticklabels([f"{a}\n（{b}）" for a, b in zip(r.rule, r["data"])], fontsize=8.5)
for i, (d, f) in enumerate(zip(r.detect_pct, r.false_alarm)):
    ax.text(d + 1, i - 0.2, f"{d:.0f}%", va="center", fontsize=8.5); ax.text(100 * f / main.is_item.sum() + 1, i + 0.2, f"{f}行", va="center", fontsize=8.5)
ax.set_xlim(0, 118); ax.legend(frameon=False, fontsize=8.5, ncol=2, loc="upper center", bbox_to_anchor=(0.4, -0.08)); ax.set_title("小計の行を機械で見つける決まりの当たり方")
save(fig, "a452_detection_rules.png", SRC, y=-0.08)
print(json.dumps(mainj, ensure_ascii=False, indent=0)[:3000]); print(bytop.to_string()); print(by_depth.to_string())
