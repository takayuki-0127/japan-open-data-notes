"""386 「以上」と「超」、「以下」と「未満」を取り違えると、何件が別の区分に入るのか
架空の会員10万人（年齢）と架空のチャージ10万件（金額）を、区分表につないで数える。乱数の種は386。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(386)
N = 100_000
AGE_B = [20, 30, 40, 50, 60, 70]                 # 「20歳以上30歳未満」…
AMT_B = [3000, 5000, 10000, 30000]               # 「3,000円以上5,000円未満」…（ボーナスの区分）
MENU = np.array([1000, 2000, 3000, 5000, 10000, 20000, 30000, 50000])
MENU_W = np.array([0.20, 0.12, 0.22, 0.20, 0.16, 0.04, 0.04, 0.02])


def make_age(n):
    ages = np.arange(18, 90)
    w = np.exp(-0.5 * ((ages - 47) / 17) ** 2) + 0.15
    return rng.choice(ages, n, p=w / w.sum())


def make_amount(n, h, r):
    """h：きりのよい金額（メニューの値）を選ぶ人の割合。残りは自由に入力（対数正規、1円単位）"""
    free = np.clip(np.round(np.exp(r.normal(np.log(4500), 0.9, n))), 500, 99_999).astype(int)
    free = np.where(free % 100 == 0, free + 1, free)       # 自由入力は、きりのよい値にならないものとする
    menu = r.choice(MENU, n, p=MENU_W)
    return np.where(r.random(n) < h, menu, free)


def n_match(x, B, lo_incl=True, hi_incl=False, shift=None):
    """各行が、いくつの区分に当てはまるか（0＝落ちる、2＝二重）と、当てはまった最初の区分の番号"""
    B = list(B)
    if shift:                                               # shift=(k, d)：k番目の境目の値を d だけずらす
        B[shift[0]] += shift[1]
    lo = np.array([-np.inf] + B, float); hi = np.array(B + [np.inf], float)
    x = np.asarray(x, float)[:, None]
    L = (x >= lo) if lo_incl else (x > lo)
    H = (x <= hi) if hi_incl else (x < hi)
    L[:, 0] = True; H[:, -1] = True                         # 両端の区分は、外側に境目がない
    M = L & H
    first = np.where(M.any(1), M.argmax(1), -1)
    return M.sum(1), first


MIX = {"正しい（以上・未満）": (True, False), "①下を「超」に（超・未満）": (False, False),
       "②上を「以下」に（以上・以下）": (True, True), "③両方（超・以下）": (False, True)}

age = make_age(N); amt = make_amount(N, 0.70, rng)
pd.DataFrame({"会員ID": np.arange(1, N + 1), "年齢": age}).to_csv(DATA / "members_age.csv", index=False)
pd.DataFrame({"チャージID": np.arange(1, N + 1), "金額": amt}).to_csv(DATA / "charges_amount.csv", index=False)

# ---- 1. 取り違えで何行が変わるか ----
rows = []
for name, x, B in [("年齢", age, AGE_B), ("チャージ額", amt, AMT_B)]:
    c0, f0 = n_match(x, B)
    assert (c0 == 1).all()
    for mix, (li, hi) in MIX.items():
        c, f = n_match(x, B, li, hi)
        rows.append({"表": name, "書き方": mix, "行": len(x), "どの区分にも入らない": int((c == 0).sum()),
                     "2つの区分に入る": int((c == 2).sum()), "別の区分に入る": int(((c == 1) & (f != f0)).sum()),
                     "変わった行の割合%": round(100 * ((c != 1) | (f != f0)).mean(), 2),
                     "つないだ後の行": int(c.sum())})
    for k, b in enumerate(B):
        rows.append({"表": name, "書き方": f"④1か所だけ（{b:,}）", "行": len(x),
                     "別の区分に入る": int((x == b).sum()), "変わった行の割合%": round(100 * (x == b).mean(), 2)})
aff = pd.DataFrame(rows); aff.to_csv(RES / "affected_rows.csv", index=False)

# 区分ごとの件数とボーナスの額（チャージ額、③両方の取り違え）
RATE = np.array([0, 1, 2, 3, 5]) / 100                     # 区分ごとのボーナスの率
LAB = ["3,000円未満", "3,000〜5,000円未満", "5,000〜1万円未満", "1万〜3万円未満", "3万円以上"]
_, f0 = n_match(amt, AMT_B); _, f3 = n_match(amt, AMT_B, False, True)
seg = pd.DataFrame({"区分": LAB, "正しい件数": np.bincount(f0, minlength=5), "③の件数": np.bincount(f3, minlength=5)})
seg["差%"] = (100 * (seg["③の件数"] / seg["正しい件数"] - 1)).round(1)
seg.to_csv(RES / "segment_counts_amount.csv", index=False)
bonus0, bonus3 = float((amt * RATE[f0]).sum()), float((amt * RATE[f3]).sum())

# ---- 2. SQL（DuckDB）で同じ数になるか ----
con = duckdb.connect(); con.execute("SET threads=1")
con.execute("CREATE TABLE charges AS SELECT * FROM read_csv_auto(?)", [str(DATA / "charges_amount.csv")])
con.execute("CREATE TABLE band(no INT, lo DOUBLE, hi DOUBLE)")
lo = [None] + AMT_B; hi = AMT_B + [None]
con.executemany("INSERT INTO band VALUES (?,?,?)", [(i, lo[i], hi[i]) for i in range(5)])
SQLS = {"正しい（以上・未満）": "(b.lo IS NULL OR c.金額 >= b.lo) AND (b.hi IS NULL OR c.金額 <  b.hi)",
        "①下を「超」に（超・未満）": "(b.lo IS NULL OR c.金額 >  b.lo) AND (b.hi IS NULL OR c.金額 <  b.hi)",
        "②上を「以下」に（以上・以下）": "(b.lo IS NULL OR c.金額 >= b.lo) AND (b.hi IS NULL OR c.金額 <= b.hi)",
        "③両方（超・以下）": "(b.lo IS NULL OR c.金額 >  b.lo) AND (b.hi IS NULL OR c.金額 <= b.hi)"}
chk = []
for mix, cond in SQLS.items():
    q = f"""SELECT COUNT(*) AS つないだ後の行, COUNT(b.no) AS 区分のついた行,
                   SUM(CASE WHEN b.no IS NULL THEN 1 ELSE 0 END) AS どの区分にも入らない
            FROM charges AS c LEFT JOIN band AS b ON {cond}"""
    a, b_, c_ = con.execute(q).fetchone()
    r = aff[(aff["表"] == "チャージ額") & (aff["書き方"] == mix)].iloc[0]
    assert b_ == r["つないだ後の行"] and c_ == r["どの区分にも入らない"], mix
    chk.append({"書き方": mix, "LEFT JOIN の後の行": a, "区分のついた行": b_, "どの区分にも入らない": c_})
pd.DataFrame(chk).to_csv(RES / "sql_check_duckdb.csv", index=False)

# ---- 3. きりのよい値に集まるほど大きいか ----
hs = np.round(np.arange(0, 0.91, 0.1), 1); heap = []
for h in hs:
    r = np.random.default_rng(3860 + int(h * 10)); x = make_amount(N, h, r)
    heap.append({"きりのよい金額を選ぶ人の割合%": int(h * 100), "境目ちょうどの行の割合%": round(100 * np.isin(x, AMT_B).mean(), 2),
                 **{f"{b:,}円ちょうど%": round(100 * (x == b).mean(), 2) for b in AMT_B}})
heap = pd.DataFrame(heap); heap.to_csv(RES / "heaping_sweep.csv", index=False)

# ---- 4. テストは何本で見つけるか ----
# 誤り（1か所だけ）：境目ごとに ①超 ②以下 ③両方 ④境目の値が+1 ⑤境目の値が−1
def out(x, B, k=None, kind=None):
    """テスト用の出力：各行の（当てはまった区分の数、最初の区分）。k番目の境目だけ kind の誤りを入れる"""
    B = list(B); x = np.asarray(x, float)
    if kind in ("+1", "-1"):
        B[k] += 1 if kind == "+1" else -1
    c, f = n_match(x, B)
    if kind in ("超", "以下", "両方"):
        at = x == B[k]
        if kind == "超":   c = np.where(at, 0, c); f = np.where(at, -1, f)      # どの区分にも入らない
        if kind == "以下": c = np.where(at, 2, c); f = np.where(at, k, f)       # 2つに入る
        if kind == "両方": f = np.where(at, k, f)                               # 1つ下の区分
    return np.stack([c, f], 1)


KINDS = ["超", "以下", "両方", "+1", "-1"]
MUT = [(t, k, kind) for t, B in (("年齢", AGE_B), ("チャージ額", AMT_B)) for k in range(len(B)) for kind in KINDS]
TB = {"年齢": AGE_B, "チャージ額": AMT_B}; DATA_X = {"年齢": age, "チャージ額": amt}


def found(tests):
    """tests：{表: テストの値の配列}。見つけた誤りの数"""
    n = 0
    for t, k, kind in MUT:
        x = np.asarray(tests[t]); n += int((out(x, TB[t]) != out(x, TB[t], k, kind)).any())
    return n


suites = {"区分の真ん中の値だけ": {"年齢": [18, 25, 35, 45, 55, 65, 80], "チャージ額": [1500, 4000, 7500, 20000, 40000]},
          "境目ちょうどの値だけ": {"年齢": AGE_B, "チャージ額": AMT_B},
          "境目と、その1つ下": {t: [v for b in B for v in (b - 1, b)] for t, B in TB.items()},
          "境目と、その上下": {t: [v for b in B for v in (b - 1, b, b + 1)] for t, B in TB.items()}}
tst = [{"テストの組み方": s, "テストの値の数": sum(len(v) for v in d.values()), "見つけた誤り": found(d), "誤りの数": len(MUT)}
       for s, d in suites.items()]
for n in (20, 100, 1000, 10000):                             # 本番のデータからでたらめに選ぶ（表ごとに n/2 件）
    r = np.random.default_rng(38600 + n)
    got = [found({t: r.choice(DATA_X[t], n // 2, replace=False) for t in TB}) for _ in range(300)]
    tst.append({"テストの組み方": f"本番のデータから{n:,}件", "テストの値の数": n, "見つけた誤り": round(float(np.mean(got)), 1),
                "誤りの数": len(MUT), "全部見つけた回の割合%": round(100 * float(np.mean(np.array(got) == len(MUT))), 1)})
tst = pd.DataFrame(tst); tst.to_csv(RES / "tests_found.csv", index=False)
# 誤りの種類ごと（境目ちょうどの値だけ）
bykind = {kind: sum((out(np.array(suites["境目ちょうどの値だけ"][t]), TB[t]) != out(np.array(suites["境目ちょうどの値だけ"][t]), TB[t], k, kd)).any()
                    for t, k, kd in MUT if kd == kind) for kind in KINDS}

# ---- 図 ----
SRC = "架空のデータ（作成者が乱数で作成、seed 386）"
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.2))
for a, (name, x, B, unit) in zip(ax, [("年齢（会員10万人）", age, AGE_B, "歳"), ("チャージ額（10万件）", amt, AMT_B, "円")]):
    v = [100 * (x == b).mean() for b in B]
    a.bar([f"{b:,}{unit}" for b in B], v, color=BLUE)
    for i, t in enumerate(v): a.text(i, t, f"{t:.1f}%", ha="center", va="bottom", fontsize=9)
    a.set_title(f"{name}：境目ちょうどの行は合わせて{sum(v):.1f}%", fontsize=11); a.set_ylabel("行の割合（%）")
    a.set_ylim(0, max(v) * 1.25)
fig.suptitle("取り違えで区分が変わるのは、境目ちょうどの値の行", y=1.02)
save(fig, "a386_affected.png", SRC)

fig, ax = plt.subplots(figsize=(7.6, 4.4))
ax.plot(heap.iloc[:, 0], heap["境目ちょうどの行の割合%"], "o-", color=ORANGE, lw=2, label="4つの境目の合計")
for b, c in zip(AMT_B, [BLUE, LIGHT, GREEN, GRAY]):
    ax.plot(heap.iloc[:, 0], heap[f"{b:,}円ちょうど%"], ".-", color=c, lw=1.2, label=f"{b:,}円ちょうど")
ax.set_xlabel("きりのよい金額を選ぶ人の割合（%）"); ax.set_ylabel("境目ちょうどの行の割合（%）")
ax.set_title("きりのよい値に集まるほど、取り違えで変わる行は増える"); ax.legend(fontsize=9, frameon=False)
save(fig, "a386_heaping.png", SRC)

fig, ax = plt.subplots(figsize=(8.6, 4.6))
lab = [f"{r['テストの組み方']}\n（{int(r['テストの値の数']):,}個）" for _, r in tst.iterrows()]
col = [GRAY, LIGHT, BLUE, BLUE] + [ORANGE] * 4
ax.barh(lab[::-1], tst["見つけた誤り"][::-1], color=col[::-1])
for i, v in enumerate(tst["見つけた誤り"][::-1]): ax.text(v + 0.5, i, f"{v:g}", va="center", fontsize=9)
ax.axvline(len(MUT), color=INK, lw=0.8, ls=":"); ax.set_xlim(0, len(MUT) + 6)
ax.set_xlabel(f"見つけた誤りの数（{len(MUT)}個のうち）"); ax.set_title("境目に入れた誤り50個を、テストはいくつ見つけたか")
ax.tick_params(axis="y", labelsize=8.5)
save(fig, "a386_tests.png", SRC + "。本番のデータから選ぶ組み方は、300回の平均")

g = lambda t, m, c: aff[(aff["表"] == t) & (aff["書き方"] == m)].iloc[0][c]
main = {"行": N, "年齢_境目ちょうどの割合%": float(g("年齢", "③両方（超・以下）", "変わった行の割合%")),
        "チャージ額_境目ちょうどの割合%": float(g("チャージ額", "③両方（超・以下）", "変わった行の割合%")),
        "チャージ額_①落ちる行": int(g("チャージ額", "①下を「超」に（超・未満）", "どの区分にも入らない")),
        "チャージ額_②つないだ後の行": int(g("チャージ額", "②上を「以下」に（以上・以下）", "つないだ後の行")),
        "ボーナスの額_正しい": bonus0, "ボーナスの額_③": bonus3, "ボーナスの額_差%": round(100 * (bonus3 / bonus0 - 1), 1),
        "年齢_1か所だけ_最小最大%": [float(aff[(aff["表"] == "年齢") & aff["書き方"].str.startswith("④")]["変わった行の割合%"].min()),
                              float(aff[(aff["表"] == "年齢") & aff["書き方"].str.startswith("④")]["変わった行の割合%"].max())],
        "誤りの数": len(MUT), "境目ちょうどだけで見つけた数_種類ごと": {k: int(v) for k, v in bykind.items()},
        "duckdb": duckdb.__version__}
json.dump(main, open(RES / "a386_main.json", "w"), ensure_ascii=False, indent=1)
print(aff.to_string()); print(seg.to_string()); print(heap.to_string()); print(tst.to_string()); print(main)
