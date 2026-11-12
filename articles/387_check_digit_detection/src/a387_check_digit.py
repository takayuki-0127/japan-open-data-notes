"""387 チェックデジットは、打ち間違いの何割を止めるのか
架空の会員番号100万件（本体11桁＋検査用の1桁）に打ち間違いを入れ、検査で止まる割合を数える。乱数の種は387。"""
import json
import numpy as np, pandas as pd, duckdb
import matplotlib.pyplot as plt
from common import *

rng = np.random.default_rng(387)
N, L = 1_000_000, 11                                   # 本体11桁
W31 = np.array([3 if i % 2 == 0 else 1 for i in range(L)][::-1])        # 右端の本体の桁から 3,1,3,1…
W27 = np.array([2 + (i % 6) for i in range(L)][::-1])                   # 右端の本体の桁から 2,3,…,7,2,…
LUHN_TAB = np.array([0, 2, 4, 6, 8, 1, 3, 5, 7, 9])                     # 2倍して、2桁なら各桁を足す


def body_sum_luhn(B):
    """本体の桁のうち、右端から1つおきを2倍（検査用の桁のすぐ左が2倍）"""
    dbl = np.zeros(B.shape[1], bool); dbl[::-1][::2] = True
    return np.where(dbl, LUHN_TAB[B], B).sum(1)


SCHEMES = ["モジュラス10（ウェイト3・1）", "モジュラス10（ルーン）", "モジュラス11（10は0に読み替え）", "モジュラス11（10になる番号は使わない）"]


def check_digit(B, s):
    if s == SCHEMES[0]: return (10 - (B * W31).sum(1) % 10) % 10
    if s == SCHEMES[1]: return (10 - body_sum_luhn(B) % 10) % 10
    r = (B * W27).sum(1) % 11; c = 11 - r                      # c は 1〜11
    return np.where(c >= 10, 0, c)                             # 10 と 11 は 0


def valid(D, s):
    B, c = D[:, :L], D[:, L]
    ok = check_digit(B, s) == c
    if s == SCHEMES[3]:
        ok &= (B * W27).sum(1) % 11 != 1                       # 検査用の値が10になる番号は、発行していない
    return ok


def issue(n, s, r):
    B = r.integers(0, 10, (n, L)); B[:, 0] = r.integers(1, 10, n)
    if s == SCHEMES[3]:                                        # 使えない番号は作り直す
        for _ in range(20):
            bad = (B * W27).sum(1) % 11 == 1
            if not bad.any(): break
            B[bad] = r.integers(0, 10, (bad.sum(), L)); B[bad, 0] = r.integers(1, 10, bad.sum())
    return np.column_stack([B, check_digit(B, s)])


# ---- 打ち間違い（12桁のどこかに入れる）。戻り値：誤りを入れた番号と、入れられた行の印 ----
def e_single(D, r):
    E = D.copy(); n = len(D); p = r.integers(0, L + 1, n)
    E[np.arange(n), p] = (D[np.arange(n), p] + r.integers(1, 10, n)) % 10
    return E, np.ones(n, bool)


def e_swap(D, r, gap=1):
    """隣どうし（gap=1）、または1つ飛ばし（gap=2）の2桁を入れ替える。同じ数字の組は、別の位置を選び直す"""
    E = D.copy(); n = len(D); done = np.zeros(n, bool)
    for _ in range(30):
        todo = ~done
        if not todo.any(): break
        idx = np.flatnonzero(todo); p = r.integers(0, L + 1 - gap, len(idx))
        a, b = D[idx, p], D[idx, p + gap]; ok = a != b
        E[idx[ok], p[ok]] = b[ok]; E[idx[ok], p[ok] + gap] = a[ok]; done[idx[ok]] = True
    return E, done


def e_twin(D, r):
    """同じ数字が2つ並んだ所（55など）を、別の同じ数字2つ（88など）に打つ"""
    E = D.copy(); n = len(D); tw = D[:, :-1] == D[:, 1:]; has = tw.any(1)
    score = np.where(tw, r.random(tw.shape), -1.0); p = score.argmax(1)        # 並びが複数あれば、でたらめに1つ
    idx = np.flatnonzero(has); new = (D[idx, p[idx]] + r.integers(1, 10, len(idx))) % 10
    E[idx, p[idx]] = new; E[idx, p[idx] + 1] = new
    return E, has


def e_two(D, r):
    E = D.copy(); n = len(D); p1 = r.integers(0, L + 1, n); p2 = (p1 + r.integers(1, L + 1, n)) % (L + 1)
    for p in (p1, p2): E[np.arange(n), p] = (D[np.arange(n), p] + r.integers(1, 10, n)) % 10
    return E, np.ones(n, bool)


def e_random(D, r):
    E = r.integers(0, 10, D.shape); E[:, 0] = r.integers(1, 10, len(D))
    return E, (E != D).any(1)


ERR = {"1桁の誤り": e_single, "隣の2桁の入れ替え": e_swap, "1つ飛ばしの入れ替え": lambda D, r: e_swap(D, r, 2),
       "同じ数字2つの誤り（55→88）": e_twin, "2桁の誤り": e_two, "まったく別の番号": e_random}
# 打ち間違いの内訳（仮定）。1桁の誤りと隣の入れ替えが大半、という置き方
MIXW = {"1桁の誤り": 0.79, "隣の2桁の入れ替え": 0.10, "1つ飛ばしの入れ替え": 0.01, "同じ数字2つの誤り（55→88）": 0.005,
        "2桁の誤り": 0.05, "まったく別の番号": 0.045}

rows = []; first = None
for s in SCHEMES:
    D = issue(N, s, np.random.default_rng(3870 + SCHEMES.index(s)))
    assert valid(D, s).all()
    if s == SCHEMES[1]: first = D
    for e, fn in ERR.items():
        E, used = fn(D, np.random.default_rng(38700 + 10 * SCHEMES.index(s) + list(ERR).index(e)))
        assert (E[used] != D[used]).any(1).all()
        stop = ~valid(E[used], s)
        rows.append({"検査の方式": s, "打ち間違い": e, "試した件数": int(used.sum()), "止まった件数": int(stop.sum()),
                     "止まった割合%": round(100 * stop.mean(), 2), "通った割合%": round(100 * (1 - stop.mean()), 2)})
det = pd.DataFrame(rows); det.to_csv(RES / "detection_by_error.csv", index=False)
piv = det.pivot(index="打ち間違い", columns="検査の方式", values="止まった割合%").loc[list(ERR), SCHEMES]
piv.to_csv(RES / "detection_table.csv")

# 理屈の値と合うか（ルーン：1桁は100%、隣の入れ替えは 09↔90 だけ通るので 88/90）
g = lambda s, e: float(det[(det["検査の方式"] == s) & (det["打ち間違い"] == e)]["止まった割合%"].iloc[0])
assert g(SCHEMES[1], "1桁の誤り") == 100 and abs(g(SCHEMES[1], "隣の2桁の入れ替え") - 100 * 88 / 90) < 0.1
assert g(SCHEMES[0], "1桁の誤り") == 100 and abs(g(SCHEMES[0], "隣の2桁の入れ替え") - 100 * 80 / 90) < 0.1
assert g(SCHEMES[3], "1桁の誤り") == 100 and g(SCHEMES[3], "隣の2桁の入れ替え") == 100

# ---- 隣の入れ替えで、どの数字の組が通るか（位置は本体の右から2・3桁目） ----
pair = {}
for s in SCHEMES[:3]:
    M = np.zeros((10, 10))
    D = issue(200_000, s, np.random.default_rng(3879))
    for a in range(10):
        for b in range(10):
            if a == b: M[a, b] = np.nan; continue
            X = D.copy(); X[:, L - 3] = a; X[:, L - 2] = b; X[:, L] = check_digit(X[:, :L], s)
            Y = X.copy(); Y[:, L - 3] = b; Y[:, L - 2] = a
            M[a, b] = 100 * (~valid(Y, s)).mean()
    pair[s] = M
    pd.DataFrame(M, index=[f"{a}" for a in range(10)], columns=[f"{b}" for b in range(10)]).to_csv(RES / f"swap_pairs_{SCHEMES.index(s)}.csv")

# ---- 100万件の入力で、誤った番号が何件通るか（仮定：入力の誤りは1%、内訳は MIXW） ----
P_ERR, M_IN = 0.01, 1_000_000
passw = {s: sum(MIXW[e] * (100 - g(s, e)) / 100 for e in ERR) for s in SCHEMES}
thr = [{"方法": "検査なし", "通った誤りの件数": M_IN * P_ERR, "打つ回数": 1}]
for s in SCHEMES: thr.append({"方法": s, "通った誤りの件数": round(M_IN * P_ERR * passw[s], 1), "打つ回数": 1})
# 二重入力：2回打って、違っていたら打ち直す。2回とも同じ誤りになるのは、①たまたま同じ ②元の紙の読み違い（2回とも同じ）
r = np.random.default_rng(38799); n2 = 2_000_000
D = issue(n2, SCHEMES[1], r)
def one_entry(D, r):
    """1%の行に、内訳どおりの誤りを入れる"""
    E = D.copy(); u = r.random(len(D)); kind = r.choice(len(ERR), len(D), p=list(MIXW.values()))
    for i, (e, fn) in enumerate(ERR.items()):
        m = (u < P_ERR) & (kind == i)
        if m.any():
            X, used = fn(D[m], r); E[m] = X
    return E
same_by_chance = []
for rep in range(5):
    E1, E2 = one_entry(D, r), one_entry(D, r)
    same_by_chance.append(int((((E1 != D).any(1)) & ((E1 == E2).all(1))).sum()))
chance_rate = float(np.mean(same_by_chance)) / n2          # 2回とも同じ誤りになった割合
for share in (0, 0.1, 0.3):
    # 誤りのうち share は「元の読み違い」で2回とも同じ。残りは別々に起きる
    n_pass = M_IN * (P_ERR * share + chance_rate * (1 - share) ** 2)
    thr.append({"方法": f"二重入力（読み違いが誤りの{int(share*100)}%）", "通った誤りの件数": round(n_pass, 1), "打つ回数": 2})
    thr.append({"方法": f"二重入力＋ルーン（読み違いが誤りの{int(share*100)}%）", "通った誤りの件数": round(n_pass * passw[SCHEMES[1]], 1), "打つ回数": 2})
thr = pd.DataFrame(thr); thr.to_csv(RES / "errors_passed_per_million.csv", index=False)

# ---- SQL（DuckDB）でルーンの検査を書いて、同じ答えか ----
smp = first[:20_000].copy(); bad, _ = e_single(smp[10_000:], np.random.default_rng(1)); smp[10_000:] = bad
nums = ["".join(map(str, x)) for x in smp]
con = duckdb.connect(); con.execute("SET threads=1")
con.execute("CREATE TABLE member(no VARCHAR)"); con.executemany("INSERT INTO member VALUES (?)", [(x,) for x in nums])
SQL = (ROOT / "src" / "01_luhn_duckdb.sql").read_text(encoding="utf-8")
got = con.execute(SQL).df()
assert (got["ok"].to_numpy() == valid(smp, SCHEMES[1])).all()
pd.DataFrame([{"行": len(got), "検査を通った行": int(got["ok"].sum()), "NumPy と同じ答えの行": int((got["ok"].to_numpy() == valid(smp, SCHEMES[1])).sum())}]).to_csv(RES / "sql_check_duckdb.csv", index=False)

# ---- 図 ----
SRC = "架空の会員番号（作成者が乱数で作成、seed 387）。12桁＝本体11桁＋検査用の1桁"
fig, ax = plt.subplots(figsize=(10.2, 4.8)); x = np.arange(len(ERR)); w = 0.2; cols = [LIGHT, BLUE, ORANGE, GREEN]
for i, s in enumerate(SCHEMES):
    v = piv[s].to_numpy(); ax.bar(x + (i - 1.5) * w, v, w, color=cols[i], label=s)
    for xi, t in zip(x, v): ax.text(xi + (i - 1.5) * w, t + 1, f"{t:.0f}", ha="center", fontsize=7)
ax.set_xticks(x); ax.set_xticklabels([e.replace("（", "\n（") for e in ERR], fontsize=9); ax.set_ylim(0, 118)
ax.set_ylabel("検査で止まった割合（%）"); ax.set_title("打ち間違いの種類ごとの、検査で止まった割合")
ax.legend(fontsize=8, frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.0))
save(fig, "a387_detection.png", SRC)

fig, ax = plt.subplots(figsize=(9.2, 5.0)); t = thr.iloc[::-1]
col = [GRAY if m == "検査なし" else (ORANGE if m.startswith("二重入力") else BLUE) for m in t["方法"]]
ax.barh(t["方法"], t["通った誤りの件数"].clip(lower=0.5), color=col); ax.set_xscale("log")
for i, v in enumerate(t["通った誤りの件数"]): ax.text(max(v, 0.5) * 1.15, i, f"{v:,.0f}件" if v >= 10 else f"{v:.1f}件", va="center", fontsize=8.5)
ax.set_xlim(0.4, 60000); ax.set_xlabel("誤ったまま通った番号（100万件の入力あたり、対数の目盛り）")
ax.set_title("100万件を入力したとき、誤った番号は何件通るか"); ax.tick_params(axis="y", labelsize=8.5)
save(fig, "a387_passed_per_million.png", SRC + "。入力の誤りを1%、内訳を1桁79%・隣の入れ替え10%などと置いた場合")

fig, axs = plt.subplots(1, 3, figsize=(11.5, 4.2))
for a, s in zip(axs, SCHEMES[:3]):
    M = pair[s]; a.imshow(np.where(np.isnan(M), np.nan, M), cmap="RdYlGn", vmin=0, vmax=100)
    for i in range(10):
        for j in range(10):
            if i != j and M[i, j] == 0: a.text(j, i, "×", ha="center", va="center", fontsize=11, color=INK)
            elif i != j and M[i, j] < 100: a.text(j, i, f"{100 - M[i, j]:.0f}", ha="center", va="center", fontsize=7.5, color=INK)
    miss = int(np.nansum(M < 100))
    a.set_xticks(range(10)); a.set_yticks(range(10)); a.set_xlabel("右の数字"); a.set_ylabel("左の数字")
    a.set_title(f"{s}\n通ることがある組：90組のうち{miss}組", fontsize=9.5)
fig.suptitle("隣の2桁を入れ替えても検査を通る数字の組（×＝いつも通る、数字＝通る割合%）", y=1.03)
save(fig, "a387_swap_pairs.png", SRC + "。本体の右から2・3桁目を入れ替えた場合")

main = {"件数": N, "止まった割合%": {s: {e: g(s, e) for e in ERR} for s in SCHEMES},
        "内訳で重みをつけた、通る割合%": {s: round(100 * passw[s], 2) for s in SCHEMES},
        "二重入力で、たまたま同じ誤りになった割合（100万件あたり）": round(chance_rate * 1e6, 2),
        "隣の入れ替えで通る組の数": {s: int(np.nansum(pair[s] < 100)) for s in SCHEMES[:3]}, "duckdb": duckdb.__version__}
json.dump(main, open(RES / "a387_main.json", "w"), ensure_ascii=False, indent=1)
print(piv.to_string()); print(thr.to_string()); print(main)
