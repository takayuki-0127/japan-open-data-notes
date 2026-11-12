"""408 件数の小さいセルを隠した集計表は、引き算で何セル分かってしまうのか
架空の「地域×年齢」の集計表（行・列の合計つき）で、小さいセルを隠し、合計からの逆算を試す。乱数の種は408。"""
import json
import numpy as np, pandas as pd, duckdb
from scipy.optimize import linprog
import matplotlib.pyplot as plt
from common import *

SEED = 408
AGE = np.array([0.05, 0.12, 0.18, 0.20, 0.18, 0.14, 0.09, 0.04])        # 8つの年齢の区分の割合
AGE_NAMES = ["20歳未満", "20代", "30代", "40代", "50代", "60代", "70代", "80歳以上"]


def make_table(r, n_rows=40, age=AGE, mu=np.log(300), sd=1.0):
    size = r.lognormal(mu, sd, n_rows)                                    # 地域ごとの利用者の多さ
    return r.poisson(size[:, None] * age[None, :])


def primary(T, t):
    """1以上 t 未満のセルを隠す（0はそのまま出す）"""
    return (T >= 1) & (T < t)


def subtract(T, H):
    """行か列の中に隠したセルが1つだけなら、合計からの引き算で分かる。これをくり返す。分かったセルの印を返す"""
    H = H.copy(); found = np.zeros_like(H)
    while True:
        rows = np.where(H.sum(1) == 1)[0]; cols = np.where(H.sum(0) == 1)[0]
        if len(rows) == 0 and len(cols) == 0:
            return found
        for i in rows:
            j = np.where(H[i])[0]
            if len(j) == 1: found[i, j[0]] = True; H[i, j[0]] = False
        for j in cols:
            i = np.where(H[:, j])[0]
            if len(i) == 1: found[i[0], j] = True; H[i[0], j] = False


def secondary(T, H):
    """行・列の中で隠したセルが1つだけにならないよう、いちばん小さい出ているセルを追加で隠す（くり返す）"""
    H = H.copy(); S = np.zeros_like(H)
    for _ in range(200):
        rows = np.where(H.sum(1) == 1)[0]; cols = np.where(H.sum(0) == 1)[0]
        if len(rows) == 0 and len(cols) == 0:
            break
        if len(rows):
            i = rows[0]; cand = np.where(~H[i])[0]
            # できれば、すでに隠したセルが2つ以上ある列から選ぶ（新しい「1つだけ」を作りにくい）
            j = min(cand, key=lambda c: (H[:, c].sum() == 0, T[i, c]))
            H[i, j] = True; S[i, j] = True
        else:
            j = cols[0]; cand = np.where(~H[:, j])[0]
            i = min(cand, key=lambda c: (H[c].sum() == 0, T[c, j]))
            H[i, j] = True; S[i, j] = True
    return H, S


def lp_bounds(T, H, lo, hi):
    """隠したセルの値について、行・列の合計と矛盾しない範囲（最小・最大）を線形計画で出す"""
    idx = np.argwhere(H); n = len(idx)
    if n == 0:
        return idx, np.zeros(0), np.zeros(0)
    rows = sorted(set(idx[:, 0])); cols = sorted(set(idx[:, 1]))
    Aeq = np.zeros((len(rows) + len(cols), n)); beq = np.zeros(len(rows) + len(cols))
    for k, (i, j) in enumerate(idx):
        Aeq[rows.index(i), k] = 1; Aeq[len(rows) + cols.index(j), k] = 1
    for a, i in enumerate(rows): beq[a] = T[i][H[i]].sum()
    for b, j in enumerate(cols): beq[len(rows) + b] = T[:, j][H[:, j]].sum()
    mn = np.zeros(n); mx = np.zeros(n)
    for k in range(n):
        c = np.zeros(n); c[k] = 1
        mn[k] = linprog(c, A_eq=Aeq, b_eq=beq, bounds=(lo, hi), method="highs").fun
        mx[k] = -linprog(-c, A_eq=Aeq, b_eq=beq, bounds=(lo, hi), method="highs").fun
    return idx, np.round(mn), np.round(mx)


# ---- 0. 例の表を1つ保存 ----
r0 = np.random.default_rng(SEED)
T0 = make_table(r0); H0 = primary(T0, 10)
ex = pd.DataFrame(T0, columns=AGE_NAMES); ex.insert(0, "地域", [f"地域{i + 1:02d}" for i in range(len(T0))]); ex["合計"] = T0.sum(1)
ex.to_csv(DATA / "example_table_true.csv", index=False)
pub = ex.copy().astype(object)
for i, j in np.argwhere(H0): pub.iat[i, j + 1] = "x"
pub.to_csv(DATA / "example_table_published.csv", index=False)

# SQL（DuckDB）：公表する前に、隠したセルが1つだけの行・列がないかを数える
long = pd.DataFrame([{"地域": f"地域{i + 1:02d}", "年齢": AGE_NAMES[j], "件数": int(T0[i, j])} for i in range(T0.shape[0]) for j in range(T0.shape[1])])
con = duckdb.connect(); con.register("cells", long)
q = """
WITH h AS (SELECT *, CASE WHEN 件数 >= 1 AND 件数 < 10 THEN 1 ELSE 0 END AS 隠す FROM cells)
SELECT '行' AS 向き, COUNT(*) AS 隠したセルが1つだけ FROM (SELECT 地域 FROM h GROUP BY 地域 HAVING SUM(隠す) = 1)
UNION ALL
SELECT '列', COUNT(*) FROM (SELECT 年齢 FROM h GROUP BY 年齢 HAVING SUM(隠す) = 1)"""
sq = con.sql(q).df()
assert sq["隠したセルが1つだけ"].tolist() == [int((H0.sum(1) == 1).sum()), int((H0.sum(0) == 1).sum())]
sq.to_csv(RES / "sql_check_duckdb.csv", index=False)

# ---- 1. 基本の設定（40地域×8区分、10未満を隠す）：1,000枚 ----
def run(n_tab, n_rows, t, seed, age=AGE, mu=np.log(300), sd=1.0, lp=0):
    r = np.random.default_rng(seed); out = []
    for k in range(n_tab):
        T = make_table(r, n_rows, age, mu, sd); H = primary(T, t)
        f = subtract(T, H); H2, S = secondary(T, H); f2 = subtract(T, H2)
        d = {"セル": T.size, "隠したセル": int(H.sum()), "引き算で分かる": int(f.sum()),
             "隠したセルが1つだけの行": int((H.sum(1) == 1).sum()), "隠したセルが1つだけの列": int((H.sum(0) == 1).sum()),
             "追加で隠したセル": int(S.sum()), "追加後に引き算で分かる": int((f2 & H).sum()),
             "隠した件数": int(T[H].sum()), "追加で隠した件数": int(T[S].sum()), "全体の件数": int(T.sum())}
        if k < lp:
            idx, mn, mx = lp_bounds(T, H, 1, t - 1)                       # 隠す決まり（1以上 t 未満）を知っている相手
            w = mx - mn
            d.update({"範囲が1つの値": int((w == 0).sum()), "範囲が3つ以内": int((w <= 2).sum()), "範囲の幅の平均": float(w.mean()) if len(w) else np.nan})
            idx2, mn2, mx2 = lp_bounds(T, H2, 0, None)                    # 追加で隠した後：どのセルが小さいかは分からない
            m = {tuple(x): (a, b) for x, a, b in zip(idx2, mn2, mx2)}
            w2 = np.array([m[tuple(x)][1] - m[tuple(x)][0] for x in np.argwhere(H)])
            lo2 = np.array([m[tuple(x)][0] for x in np.argwhere(H)]); hi2 = np.array([m[tuple(x)][1] for x in np.argwhere(H)])
            d.update({"追加後_範囲が1つの値": int((w2 == 0).sum()), "追加後_範囲が3つ以内": int((w2 <= 2).sum()),
                      "追加後_10未満と分かる": int((hi2 < t).sum()), "追加後_範囲の幅の平均": float(w2.mean()) if len(w2) else np.nan})
        out.append(d)
    return pd.DataFrame(out)


B = run(1000, 40, 10, SEED + 1, lp=100)
B.to_csv(RES / "base_1000_tables.csv", index=False)
tot = B.sum()
base = {"表の数": 1000, "1枚のセル": 320, "隠したセル(平均)": round(B["隠したセル"].mean(), 1),
        "隠したセルの割合(%)": round(100 * tot["隠したセル"] / tot["セル"], 1),
        "引き算で分かる割合(%)": round(100 * tot["引き算で分かる"] / tot["隠したセル"], 1),
        "1セル以上分かる表(%)": round(100 * (B["引き算で分かる"] > 0).mean(), 1),
        "追加で隠したセル(平均)": round(B["追加で隠したセル"].mean(), 1),
        "追加で隠したセル÷最初に隠したセル(%)": round(100 * tot["追加で隠したセル"] / tot["隠したセル"], 1),
        "追加後に引き算で分かる割合(%)": round(100 * tot["追加後に引き算で分かる"] / tot["隠したセル"], 2),
        "隠した件数の割合(%)": round(100 * tot["隠した件数"] / tot["全体の件数"], 2),
        "追加で隠した件数の割合(%)": round(100 * tot["追加で隠した件数"] / tot["全体の件数"], 2)}
L = B.iloc[:100]; lt = L.sum()
lpres = {"表の数": 100, "隠したセル": int(lt["隠したセル"]),
         "値が1つに決まる(%)": round(100 * lt["範囲が1つの値"] / lt["隠したセル"], 1), "3つ以内に絞れる(%)": round(100 * lt["範囲が3つ以内"] / lt["隠したセル"], 1),
         "範囲の幅の平均": round(float(np.average(L["範囲の幅の平均"].dropna(), weights=L.loc[L["範囲の幅の平均"].notna(), "隠したセル"])), 2),
         "追加後_値が1つに決まる(%)": round(100 * lt["追加後_範囲が1つの値"] / lt["隠したセル"], 1),
         "追加後_3つ以内に絞れる(%)": round(100 * lt["追加後_範囲が3つ以内"] / lt["隠したセル"], 1),
         "追加後_10未満と分かる(%)": round(100 * lt["追加後_10未満と分かる"] / lt["隠したセル"], 1),
         "追加後_範囲の幅の平均": round(float(np.average(L["追加後_範囲の幅の平均"].dropna(), weights=L.loc[L["追加後_範囲の幅の平均"].notna(), "隠したセル"])), 1)}

# ---- 2. 設定を変える ----
rows = []
def summ(name, D):
    t = D.sum()
    rows.append({"設定": name, "隠したセルの割合(%)": round(100 * t["隠したセル"] / t["セル"], 1),
                 "引き算で分かる割合(%)": round(100 * t["引き算で分かる"] / max(t["隠したセル"], 1), 1),
                 "1セル以上分かる表(%)": round(100 * (D["引き算で分かる"] > 0).mean(), 1),
                 "追加で隠したセル÷最初に隠したセル(%)": round(100 * t["追加で隠したセル"] / max(t["隠したセル"], 1), 1),
                 "追加で隠した件数の割合(%)": round(100 * t["追加で隠した件数"] / t["全体の件数"], 2)})
for t in (3, 5, 10, 20):
    summ(f"隠す境目：{t}未満（40地域）", run(500, 40, t, SEED + 10 + t))
for n in (5, 10, 20, 40, 100, 200):
    summ(f"地域の数：{n}（10未満を隠す）", run(500, n, 10, SEED + 100 + n))
for m, lab in ((np.log(100), "小さい地域が多い（中央100人）"), (np.log(300), "基本（中央300人）"), (np.log(1000), "大きい地域が多い（中央1,000人）"), (np.log(3000), "中央3,000人")):
    summ(f"地域の大きさ：{lab}", run(500, 40, 10, SEED + 300 + int(m * 10), mu=m))
V = pd.DataFrame(rows); V.to_csv(RES / "by_setting.csv", index=False)

# 隠したセルの数ごとに、引き算で分かる割合（基本の設定）
B["隠した割合の区分"] = pd.cut(100 * B["隠したセル"] / B["セル"], [0, 5, 10, 15, 20, 30, 100])
G = B.groupby("隠した割合の区分", observed=True).agg(表=("セル", "size"), 隠したセル=("隠したセル", "sum"), 分かる=("引き算で分かる", "sum")).reset_index()
G["引き算で分かる割合(%)"] = (100 * G["分かる"] / G["隠したセル"]).round(1); G["隠した割合の区分"] = G["隠した割合の区分"].astype(str)
G.to_csv(RES / "recover_by_share_hidden.csv", index=False)

main = {"基本（40地域×8区分・10未満を隠す・1,000枚）": base, "合計と矛盾しない範囲（100枚）": lpres,
        "例の表": {"隠したセル": int(H0.sum()), "引き算で分かる": int(subtract(T0, H0).sum()), "追加で隠したセル": int(secondary(T0, H0)[1].sum())},
        "設定を変える": V.set_index("設定").to_dict("index")}
json.dump(main, open(RES / "a408_main.json", "w"), ensure_ascii=False, indent=1)

# ---- 図 ----
SRC = "架空の集計表（作成者が乱数で作成、seed 408）"
# 図1：例の表（上15地域）— 隠したセル、引き算で分かるセル
f0 = subtract(T0, H0); n_show = 14
show = sorted(set(np.where(f0.any(1))[0].tolist()) | set(range(40)[: n_show - int(f0.any(1).sum())]))[:n_show]   # 分かるセルのある地域を必ず入れる
fig, ax = plt.subplots(figsize=(9, 5.2)); ax.axis("off")
cw, ch = 1.0, 1.0
for j, nm in enumerate(AGE_NAMES + ["合計"]):
    ax.text(1.6 + j * cw + cw / 2, n_show + 0.45, nm, ha="center", va="center", fontsize=8.5)
for i_, i in enumerate(show):
    ax.text(1.5, n_show - i_ - 0.5, f"地域{i + 1:02d}", ha="right", va="center", fontsize=8.5)
    for j in range(9):
        x, y = 1.6 + j * cw, n_show - i_ - 1
        if j < 8 and H0[i, j]:
            col = ORANGE if f0[i, j] else LIGHT
            ax.add_patch(plt.Rectangle((x + 0.04, y + 0.06), cw - 0.08, ch - 0.12, color=col))
            ax.text(x + cw / 2, y + 0.5, f"x→{T0[i, j]}" if f0[i, j] else "x", ha="center", va="center", fontsize=9, color="white" if f0[i, j] else INK)
        else:
            v = T0[i, j] if j < 8 else T0[i].sum()
            ax.text(x + cw / 2, y + 0.5, f"{v:,}", ha="center", va="center", fontsize=9, color=GRAY if j == 8 else INK)
ax.set_xlim(0, 11); ax.set_ylim(-0.2, n_show + 1)
ax.set_title(f"小さいセルを x で隠した表（40地域のうち{n_show}地域）。橙は、合計からの引き算で分かるセル", fontsize=11)
save(fig, "a408_example_table.png", SRC + "。列の合計は40地域分で、ここには出していない", y=0.04)

# 図2：設定ごとに、引き算で分かる割合
fig, axes = plt.subplots(1, 3, figsize=(12, 3.9), sharey=True)
for ax, key, ttl in zip(axes, ["隠す境目", "地域の数", "地域の大きさ"], ["隠す境目（40地域）", "地域の数（10未満を隠す）", "地域の大きさ（40地域・10未満）"]):
    s = V[V["設定"].str.startswith(key)]
    lab = [x.split("：")[1].split("（")[0] for x in s["設定"]]
    ax.bar(range(len(s)), s["引き算で分かる割合(%)"], color=ORANGE)
    for i, v in enumerate(s["引き算で分かる割合(%)"]):
        ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=9)
    lab = [l.replace("小さい地域が多い", "中央100人").replace("基本", "中央300人").replace("大きい地域が多い", "中央1,000人") for l in lab]
    ax.set_xticks(range(len(s))); ax.set_xticklabels([f"{l}\n({h:.0f}%)" for l, h in zip(lab, s["隠したセルの割合(%)"])], fontsize=8); ax.set_title(ttl, fontsize=10.5)
axes[0].set_ylabel("隠したセルのうち、引き算で分かる割合（%）"); axes[0].set_ylim(0, 115)
fig.suptitle("隠したセルが少ない表ほど、引き算で分かる", y=1.02)
save(fig, "a408_recover_by_setting.png", SRC + "。かっこ内は、全セルのうち隠したセルの割合", y=-0.04)

# 図3：追加で隠す前と後
fig, axes = plt.subplots(1, 2, figsize=(10, 4.0))
ax = axes[0]
names = ["引き算で\nぴったり分かる", "合計と合う値が\n1つしかない", "3つ以内に\n絞れる"]
before = [base["引き算で分かる割合(%)"], lpres["値が1つに決まる(%)"], lpres["3つ以内に絞れる(%)"]]
after = [base["追加後に引き算で分かる割合(%)"], lpres["追加後_値が1つに決まる(%)"], lpres["追加後_3つ以内に絞れる(%)"]]
x = np.arange(3); w = 0.38
ax.bar(x - w / 2, before, w, color=ORANGE, label="小さいセルだけ隠す"); ax.bar(x + w / 2, after, w, color=BLUE, label="追加でも隠す")
for i, (a, b) in enumerate(zip(before, after)):
    ax.text(i - w / 2, a + 1, f"{a:.1f}%", ha="center", fontsize=9); ax.text(i + w / 2, b + 1, f"{b:.1f}%", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(names, fontsize=9); ax.set_ylim(0, max(before) * 1.2); ax.set_ylabel("最初に隠したセルのうちの割合（%）"); ax.legend(frameon=False, fontsize=9); ax.set_title("分かってしまうセル", fontsize=11)
ax = axes[1]
s = V[V["設定"].str.startswith("隠す境目")]
ax.bar(range(len(s)), s["追加で隠したセル÷最初に隠したセル(%)"], color=GRAY)
for i, (v, c) in enumerate(zip(s["追加で隠したセル÷最初に隠したセル(%)"], s["追加で隠した件数の割合(%)"])):
    ax.text(i, v + 1, f"{v:.0f}%\n(件数の{c:.1f}%)", ha="center", fontsize=8.5)
ax.set_xticks(range(len(s))); ax.set_xticklabels([x.split("：")[1].split("（")[0] for x in s["設定"]]); ax.set_ylim(0, s["追加で隠したセル÷最初に隠したセル(%)"].max() * 1.35)
ax.set_ylabel("追加で隠したセル÷最初に隠したセル（%）"); ax.set_title("追加で隠すセルの数（隠す境目ごと）", fontsize=11)
save(fig, "a408_secondary_suppression.png", SRC + "。左は基本の設定（40地域×8区分、10未満を隠す）", y=-0.03)
print(json.dumps({k: main[k] for k in list(main)[:3]}, ensure_ascii=False, indent=1)); print(V.to_string()); print(G.to_string())
