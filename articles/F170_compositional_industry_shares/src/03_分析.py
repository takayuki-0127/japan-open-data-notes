"""03 分析：産業の構成比を「割合のまま」回帰に入れたときと、対数比（ilr）に直したときを比べる。

A. 構成比を説明変数にする（目的変数：1人あたり地方税の対数）
   - 割合のまま：どの産業を「基準」として落とすかで、製造業の係数がどう変わるか
   - ilr（ピボット座標）：製造業の「ほかの産業の幾何平均に対する比」の係数は、並べ方によらず1つに決まる
B. 割合どうしの相関
   - 一部の産業だけを取り出して割合を計算し直すと、相関の符号が入れ替わるか（部分組成での不整合）
   - 各産業の人数を都道府県の間で独立に並べ替えても、割合にすると負の相関が生まれるか
C. 構成比を目的変数にする（説明変数：可住地人口密度の対数）
   - 割合ごとの最小二乗と、ilr 回帰の予測を比べる（0 未満の予測、交差検証の誤差）
D. 頑健性：産業の分け方（3・6・10）、変換の種類（alr・clr・ilr）、0 の扱い、年、目的変数、単位（都道府県・市区町村）

結果は results/ に CSV と summary.json で書き出す。乱数の種は 170。
"""
import json
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
RES = BASE / "results"
RES.mkdir(exist_ok=True)
rng = np.random.default_rng(170)

# ---------------- 産業の分け方 ----------------
G6 = {"一次": [1, 2], "建設・鉱業": [3, 4], "製造": [5], "流通": [6, 8, 9],
      "知識系": [7, 10, 11, 12], "生活・福祉": [13, 14, 15, 16, 17, 18]}
G3 = {"一次": [1, 2], "二次": [3, 4, 5], "三次": list(range(6, 19))}
G10 = {"一次": [1, 2], "建設・鉱業": [3, 4], "製造": [5], "電気・運輸": [6, 8], "卸売・小売": [9],
       "情報・金融・不動産": [7, 10, 11], "学術・専門": [12], "宿泊・飲食・生活": [13, 14],
       "医療・福祉": [16], "教育・その他": [15, 17, 18]}
MANU = {"G3": "二次", "G6": "製造", "G10": "製造"}


EXCLUDED = {}


def load(year):
    d = pd.read_csv(BASE / "data" / f"muni_{year}.csv")
    d["pref"] = d.area_code.str[1:3]
    ind = [c for c in d.columns if c.startswith("ind")]
    # 国勢調査の人口が 0 の町（原発事故の避難指示区域）は、1人あたりの値が作れないので除く
    bad = (d["pop"] <= 0) | (d["tax"] <= 0) | (d["hab"] <= 0) | (d[ind].sum(1) == 0)
    EXCLUDED[year] = int(bad.sum())
    return d[~bad].reset_index(drop=True)


def counts(d, groups):
    return np.column_stack([d[[f"ind{i:02d}" for i in v]].sum(1).values for v in groups.values()]).astype(float)


def pref_table(d):
    num = [c for c in d.columns if c not in ("area_code", "pref")]
    return d.groupby("pref")[num].sum().reset_index()


def close(X):
    return X / X.sum(1, keepdims=True)


def mult_repl(C, delta):
    """0 の人数を delta 人に置き換え、ほかの割合を比を保ったまま縮める（乗法的置換）。"""
    P = close(C)
    tot = C.sum(1, keepdims=True)
    z = C == 0
    dl = np.where(z, delta / tot, 0.0)
    return np.where(z, dl, P * (1 - dl.sum(1, keepdims=True)))


def ilr_pivot(P, first, order=None):
    """first 番目の部分を先頭にしたピボット座標。order は残りの並べ方。"""
    D = P.shape[1]
    rest = [j for j in range(D) if j != first]
    if order is not None:
        rest = [rest[k] for k in order]
    idx = [first] + rest
    L = np.log(P[:, idx])
    Z = np.empty((P.shape[0], D - 1))
    for k in range(D - 1):
        Z[:, k] = np.sqrt((D - k - 1) / (D - k)) * (L[:, k] - L[:, k + 1:].mean(1))
    return Z


def ilr_inv(Z):
    """ilr_pivot(P, 0) の逆変換（並べ替えなし）。"""
    n, Dm = Z.shape
    D = Dm + 1
    L = np.zeros((n, D))  # 最後の部分の対数を 0 に置き、後ろから順に組み立てる
    for k in range(Dm - 1, -1, -1):
        c = np.sqrt((D - k - 1) / (D - k))
        L[:, k] = Z[:, k] / c + L[:, k + 1:].mean(1)
    return close(np.exp(L - L.max(1, keepdims=True)))


def ols(X, y):
    X1 = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    e = y - X1 @ b
    n, k = X1.shape
    s2 = e @ e / (n - k)
    cov = s2 * np.linalg.pinv(X1.T @ X1)
    r2 = 1 - e @ e / ((y - y.mean()) @ (y - y.mean()))
    return b, np.sqrt(np.diag(cov)), r2, e


def hc1(X, y):
    """頑健な標準誤差（HC1）。"""
    X1 = np.column_stack([np.ones(len(y)), X])
    b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    e = y - X1 @ b
    n, k = X1.shape
    B = np.linalg.pinv(X1.T @ X1)
    V = B @ (X1.T * e ** 2) @ X1 @ B * n / (n - k)
    return b, np.sqrt(np.diag(V))


def loo_rmse(X, y):
    X1 = np.column_stack([np.ones(len(y)), X])
    H = X1 @ np.linalg.pinv(X1.T @ X1) @ X1.T
    b, *_ = np.linalg.lstsq(X1, y, rcond=None)
    e = y - X1 @ b
    return float(np.sqrt(np.mean((e / (1 - np.diag(H))) ** 2)))


def outcome(t, kind):
    if kind == "tax":
        return np.log(t["tax"].values / t["pop"].values)
    return (t["in_"].values - t["out"].values) / t["pop"].values * 1000


# ---------------- A. 説明変数としての構成比 ----------------
def part_A(t, groups, kind="tax", delta=0.5, se="hc1"):
    names = list(groups)
    C = counts(t, groups)
    P = mult_repl(C, delta) if (C == 0).any() else close(C)
    y = outcome(t, kind)
    D = len(names)
    m = names.index(MANU[{3: "G3", 6: "G6", 10: "G10"}[D]])
    rows = []
    # 割合のまま：基準を1つずつ変える（係数は +1ポイントあたり。目的変数が対数なので ×100 で約%）
    for r in range(D):
        if r == m:
            continue
        keep = [j for j in range(D) if j != r]
        b, s = hc1(P[:, keep], y)
        k = keep.index(m) + 1
        rows.append({"model": "割合のまま", "基準（落とした産業）": names[r], "coef": b[k] * 0.01, "se": s[k] * 0.01})
    # 割合を1つだけ入れる（ほかを無視）
    b, s = hc1(P[:, [m]], y)
    rows.append({"model": "製造の割合だけ", "基準（落とした産業）": "（ほかを無視）", "coef": b[1] * 0.01, "se": s[1] * 0.01})
    # ilr ピボット：製造を先頭に。係数は「製造÷ほかの幾何平均」が 10% 大きいとき
    Z = ilr_pivot(P, m)
    b, s = hc1(Z, y)
    f = np.sqrt((D - 1) / D) * np.log(1.1)
    rows.append({"model": "ilr（製造÷ほか）", "基準（落とした産業）": "（なし）", "coef": b[1] * f, "se": s[1] * f})
    # 並べ方を変えても製造の係数が同じか
    alt = []
    for _ in range(20):
        Z2 = ilr_pivot(P, m, order=rng.permutation(D - 1))
        alt.append(hc1(Z2, y)[0][1] * f)
    # 当てはまり
    r2_share = ols(P[:, [j for j in range(D) if j != (0 if m != 0 else 1)]], y)[2]
    r2_ilr = ols(Z, y)[2]
    fit = {"R2_割合": r2_share, "R2_ilr": r2_ilr,
           "LOO_割合": loo_rmse(P[:, [j for j in range(D) if j != (0 if m != 0 else 1)]], y),
           "LOO_ilr": loo_rmse(Z, y), "ilr並べ替えの最大差": float(np.max(np.abs(np.array(alt) - rows[-1]["coef"])))}
    df = pd.DataFrame(rows)
    sh = df[df.model == "割合のまま"]
    sig = sh[np.abs(sh.coef) > 1.96 * sh.se]
    summ = {"割合のまま_最小": float(sh.coef.min()), "割合のまま_最大": float(sh.coef.max()),
            "割合のまま_正で有意": int((sig.coef > 0).sum()), "割合のまま_負で有意": int((sig.coef < 0).sum()),
            "割合のまま_有意でない": int(len(sh) - len(sig)),
            "符号が割れる": bool(sh.coef.min() < 0 < sh.coef.max()),
            "ilr": float(df.coef.iloc[-1]), "ilr_se": float(df.se.iloc[-1]),
            "製造だけ": float(df.coef.iloc[-2]), "製造だけ_se": float(df.se.iloc[-2]), **fit}
    return df, summ


def all_targets_A(t, groups, kind="tax"):
    """製造以外も含め、各産業について「基準しだいで符号が割れるか」。"""
    names = list(groups)
    C = counts(t, groups)
    P = mult_repl(C, 0.5) if (C == 0).any() else close(C)
    y = outcome(t, kind)
    D = len(names)
    out = []
    for m in range(D):
        cs = []
        for r in range(D):
            if r == m:
                continue
            keep = [j for j in range(D) if j != r]
            b, s = hc1(P[:, keep], y)
            k = keep.index(m) + 1
            cs.append((b[k], s[k]))
        cs = np.array(cs)
        sigpos = int(((cs[:, 0] - 1.96 * cs[:, 1]) > 0).sum())
        signeg = int(((cs[:, 0] + 1.96 * cs[:, 1]) < 0).sum())
        Z = ilr_pivot(P, m)
        b, s = hc1(Z, y)
        out.append({"産業": names[m], "割合_最小": cs[:, 0].min() * 0.01, "割合_最大": cs[:, 0].max() * 0.01,
                    "正で有意": sigpos, "負で有意": signeg,
                    "ilr_10%": b[1] * np.sqrt((D - 1) / D) * np.log(1.1),
                    "ilr_se": s[1] * np.sqrt((D - 1) / D) * np.log(1.1)})
    return pd.DataFrame(out)


summary = {}
d26 = load("2026")
d21 = load("2021")
p26 = pref_table(d26)
p21 = pref_table(d21)

A_pref, sA_pref = part_A(p26, G6)
A_muni, sA_muni = part_A(d26, G6)
A_pref.to_csv(RES / "A_reference_pref.csv", index=False)
A_muni.to_csv(RES / "A_reference_muni.csv", index=False)
summary["A_pref_G6"] = sA_pref
summary["A_muni_G6"] = sA_muni
T_pref = all_targets_A(p26, G6)
T_muni = all_targets_A(d26, G6)
T_pref.to_csv(RES / "A_all_targets_pref.csv", index=False)
T_muni.to_csv(RES / "A_all_targets_muni.csv", index=False)
summary["A_targets_split_pref"] = int(((T_pref["正で有意"] > 0) & (T_pref["負で有意"] > 0)).sum())
summary["A_targets_split_muni"] = int(((T_muni["正で有意"] > 0) & (T_muni["負で有意"] > 0)).sum())
summary["A_targets_signchange_pref"] = int(((T_pref["割合_最小"] < 0) & (T_pref["割合_最大"] > 0)).sum())
summary["A_targets_signchange_muni"] = int(((T_muni["割合_最小"] < 0) & (T_muni["割合_最大"] > 0)).sum())

# 変換の種類：alr・clr・ilr で当てはまり（予測値）が同じか
def transforms_same(t, groups):
    C = counts(t, groups)
    P = mult_repl(C, 0.5) if (C == 0).any() else close(C)
    y = outcome(t, "tax")
    L = np.log(P)
    alr = L[:, :-1] - L[:, [-1]]
    clr = L - L.mean(1, keepdims=True)
    ilr = ilr_pivot(P, 0)
    preds = []
    for X in (alr, clr, ilr):
        X1 = np.column_stack([np.ones(len(y)), X])
        b = np.linalg.pinv(X1) @ y
        preds.append(X1 @ b)
    return float(max(np.abs(preds[0] - preds[1]).max(), np.abs(preds[0] - preds[2]).max()))


summary["D_transform_maxdiff_pref"] = transforms_same(p26, G6)
summary["D_transform_maxdiff_muni"] = transforms_same(d26, G6)

# ---------------- B. 割合どうしの相関 ----------------
def corr_pairs(P):
    R = np.corrcoef(P.T)
    return R


def part_B(t, groups, nperm=500):
    names = list(groups)
    C = counts(t, groups)
    P = close(C)
    D = len(names)
    Rfull = corr_pairs(P)
    Pz = mult_repl(C, 0.5) if (C == 0).any() else P
    # 1つの産業を除いて割合を計算し直す（全 D 通り）
    flips, total, rows = 0, 0, []
    for drop in range(D):
        keep = [j for j in range(D) if j != drop]
        Rs = corr_pairs(close(C[:, keep]))
        for a, b in combinations(range(D - 1), 2):
            ra, rb = keep[a], keep[b]
            f = np.sign(Rfull[ra, rb]) != np.sign(Rs[a, b])
            rows.append({"除いた産業": names[drop], "a": names[ra], "b": names[rb],
                         "全体での相関": Rfull[ra, rb], "除いた後の相関": Rs[a, b], "符号が変わる": bool(f)})
            flips += f
            total += 1
    # 2つ除く（大きい2つ）
    big = np.argsort(-P.mean(0))[:2]
    keep = [j for j in range(D) if j not in big]
    Rs = corr_pairs(close(C[:, keep]))
    fl2 = [np.sign(Rfull[keep[a], keep[b]]) != np.sign(Rs[a, b]) for a, b in combinations(range(len(keep)), 2)]
    # 対数比の分散（どの部分組成でも同じ）
    L = np.log(Pz)
    V = np.var(L[:, :, None] - L[:, None, :], axis=0)
    Ls = np.log(close(Pz[:, keep]))
    Vs = np.var(Ls[:, :, None] - Ls[:, None, :], axis=0)
    vdiff = float(np.abs(V[np.ix_(keep, keep)] - Vs).max())
    # 並べ替え：人数の間の関係を壊しても、割合では負の相関が出るか
    iu = np.triu_indices(D, 1)
    pc, cc = [], []
    for _ in range(nperm):
        Cp = np.column_stack([rng.permutation(C[:, j]) for j in range(D)])
        pc.append(np.corrcoef(close(Cp).T)[iu].mean())
        cc.append(np.corrcoef(Cp.T)[iu].mean())
    return pd.DataFrame(rows), {
        "ペア数": int(total), "符号が変わる": int(flips), "割合": float(flips / total),
        "大きい2つを除く_ペア": len(fl2), "大きい2つを除く_符号が変わる": int(sum(fl2)),
        "除いた2産業": [names[j] for j in big],
        "対数比分散の差": vdiff,
        "並べ替え_割合の平均相関": float(np.mean(pc)), "並べ替え_割合の平均相関_95": [float(np.percentile(pc, 2.5)), float(np.percentile(pc, 97.5))],
        "並べ替え_人数の平均相関": float(np.mean(cc)), "理論値_-1/(D-1)": -1 / (D - 1),
        "実データ_割合の平均相関": float(Rfull[iu].mean())}


B_pref, sB_pref = part_B(p26, G10)
B_muni, sB_muni = part_B(d26, G10, nperm=200)
B_pref.to_csv(RES / "B_subcomposition_pref.csv", index=False)
summary["B_pref_G10"] = sB_pref
summary["B_muni_G10"] = sB_muni
summary["B_pref_G6"] = part_B(p26, G6)[1]

# ---------------- C. 目的変数としての構成比 ----------------
def design(x):
    return np.column_stack([x, x ** 2])


def part_C(t, groups, delta=0.5, k=5):
    names = list(groups)
    C = counts(t, groups)
    P = mult_repl(C, delta) if (C == 0).any() else close(C)
    x = np.log(t["pop"].values / t["hab"].values)
    X = design(x)
    n = len(x)
    folds = rng.permutation(n) % k
    out = {}
    pred_share = np.zeros_like(P)
    pred_ilr = np.zeros_like(P)
    for f in range(k):
        tr, te = folds != f, folds == f
        X1tr = np.column_stack([np.ones(tr.sum()), X[tr]])
        X1te = np.column_stack([np.ones(te.sum()), X[te]])
        B = np.linalg.lstsq(X1tr, P[tr], rcond=None)[0]
        pred_share[te] = X1te @ B
        Z = ilr_pivot(P[tr], 0)
        Bz = np.linalg.lstsq(X1tr, Z, rcond=None)[0]
        pred_ilr[te] = ilr_inv(X1te @ Bz)

    def aitch(A, B):
        A = np.clip(A, 1e-9, None)
        A = close(A)
        la = np.log(A) - np.log(A).mean(1, keepdims=True)
        lb = np.log(B) - np.log(B).mean(1, keepdims=True)
        return np.sqrt(((la - lb) ** 2).sum(1))

    # 全データで当てはめた予測
    X1 = np.column_stack([np.ones(n), X])
    Bfull = np.linalg.lstsq(X1, P, rcond=None)[0]
    fit_share = X1 @ Bfull
    Zf = ilr_pivot(P, 0)
    fit_ilr = ilr_inv(X1 @ np.linalg.lstsq(X1, Zf, rcond=None)[0])
    neg = fit_share < 0
    out = {"件数": n, "0未満の予測がある件数": int(neg.any(1).sum()),
           "0未満の予測_産業別": {names[j]: int(neg[:, j].sum()) for j in range(len(names))},
           "CV_RMSE_割合のまま_pt": float(np.sqrt(np.mean((pred_share - P) ** 2)) * 100),
           "CV_RMSE_ilr_pt": float(np.sqrt(np.mean((pred_ilr - P) ** 2)) * 100),
           "CV_Aitchison_割合のまま": float(np.median(aitch(pred_share, P))),
           "CV_Aitchison_ilr": float(np.median(aitch(pred_ilr, P))),
           "CV_0未満の予測件数_割合のまま": int((pred_share < 0).any(1).sum())}
    # 産業ごとの CV 誤差（相対誤差：小さい産業で差が出る）
    rel = {}
    for j, nm in enumerate(names):
        rel[nm] = {"割合のまま": float(np.median(np.abs(pred_share[:, j] - P[:, j]) / P[:, j])),
                   "ilr": float(np.median(np.abs(pred_ilr[:, j] - P[:, j]) / P[:, j]))}
    out["CV_相対誤差の中央値"] = rel
    grid = np.linspace(x.min(), x.max(), 60)
    Xg = np.column_stack([np.ones(60), design(grid)])
    curves = pd.DataFrame({"logdens": grid})
    Bz = np.linalg.lstsq(X1, Zf, rcond=None)[0]
    Pg_ilr = ilr_inv(Xg @ Bz)
    Pg_sh = Xg @ Bfull
    for j, nm in enumerate(names):
        curves[f"{nm}_割合のまま"] = Pg_sh[:, j]
        curves[f"{nm}_ilr"] = Pg_ilr[:, j]
    return out, curves, x, P


sC, curves, xC, PC = part_C(d26, G6)
curves.to_csv(RES / "C_curves_muni.csv", index=False)
pd.DataFrame(np.column_stack([xC, PC]), columns=["logdens"] + list(G6)).to_csv(RES / "C_points_muni.csv", index=False)
summary["C_muni_G6"] = sC
summary["C_muni_G10"] = part_C(d26, G10)[0]
summary["C_muni_G3"] = part_C(d26, G3)[0]

# ---------------- D. 頑健性 ----------------
rob = []


def add(label, s):
    rob.append({"条件": label, "割合のまま_最小": s["割合のまま_最小"], "割合のまま_最大": s["割合のまま_最大"],
                "正で有意": s["割合のまま_正で有意"], "負で有意": s["割合のまま_負で有意"],
                "ilr": s["ilr"], "ilr_se": s["ilr_se"], "製造だけ": s["製造だけ"], "製造だけ_se": s["製造だけ_se"],
                "R2_割合": s["R2_割合"], "R2_ilr": s["R2_ilr"], "LOO_割合": s["LOO_割合"], "LOO_ilr": s["LOO_ilr"]})


add("基本：都道府県・6分類・2021年センサス・地方税", sA_pref)
add("市区町村・6分類", sA_muni)
for nm, g in (("3分類", G3), ("10分類", G10)):
    add(f"都道府県・{nm}", part_A(p26, g)[1])
    add(f"市区町村・{nm}", part_A(d26, g)[1])
add("都道府県・6分類・東京を除く", part_A(p26[p26.pref != "13"].reset_index(drop=True), G6)[1])
add("都道府県・6分類・2016年センサス（SSDSE-A-2021）", part_A(p21, G6)[1])
add("市区町村・6分類・2016年センサス", part_A(d21, G6)[1])
add("都道府県・6分類・目的変数を転入超過率に", part_A(p26, G6, kind="mig")[1])
add("市区町村・6分類・目的変数を転入超過率に", part_A(d26, G6, kind="mig")[1])
for dl in (0.1, 1.0, 5.0):
    add(f"市区町村・10分類・0を{dl}人に置換", part_A(d26, G10, delta=dl)[1])
R = pd.DataFrame(rob)
R.to_csv(RES / "D_robustness.csv", index=False)
summary["D_robustness_rows"] = len(R)
summary["D_split_count"] = int(((R["割合のまま_最小"] < 0) & (R["割合のまま_最大"] > 0)).sum())

# 0 の扱い（18産業・市区町村）：ilr ピボットの密度の係数が δ でどれくらい動くか
G18 = {f"ind{i:02d}": [i] for i in range(1, 19)}
ind_names = pd.read_csv(BASE / "data" / "industries.csv").name.tolist()
C18 = counts(d26, G18)
xd = np.log(d26["pop"].values / d26["hab"].values)
zero_rows = []
zero_info = {"0を含む市区町村": int((C18 == 0).any(1).sum()),
             "0の数_産業別": {ind_names[j]: int((C18[:, j] == 0).sum()) for j in range(18)}}
for dl in (0.01, 0.1, 0.5, 1.0):
    P18 = mult_repl(C18, dl)
    for j in range(18):
        Z = ilr_pivot(P18, j)
        b, s = hc1(xd[:, None], Z[:, 0])
        zero_rows.append({"delta": dl, "産業": ind_names[j], "0の数": int((C18[:, j] == 0).sum()),
                          "密度の係数": b[1], "se": s[1]})
Zrows = pd.DataFrame(zero_rows)
Zrows.to_csv(RES / "D_zero_handling.csv", index=False)
piv = Zrows.pivot(index="産業", columns="delta", values="密度の係数")
spread = (piv.max(1) - piv.min(1)) / piv.abs().mean(1)
zero_info["係数の動き（最大−最小）÷平均の絶対値"] = {k: float(v) for k, v in spread.items()}
zcount = Zrows.drop_duplicates("産業").set_index("産業")["0の数"]
zero_info["0が10件未満の産業の動きの中央値"] = float(spread[zcount < 10].median())
zero_info["0が300件以上の産業の動きの中央値"] = float(spread[zcount >= 300].median())
zero_info["製造業の係数_δ別"] = {str(k): float(v) for k, v in piv.loc["製造業"].items()}
zero_info["漁業の係数_δ別"] = {str(k): float(v) for k, v in piv.loc["漁業"].items()}
summary["D_zero"] = zero_info

# 3分類（国勢調査の第1〜3次産業就業者）でも同じか：代替案のチェック
def part_A_census(t):
    C = t[["sec1", "sec2", "sec3"]].values.astype(float)
    P = close(C)
    y = outcome(t, "tax")
    res = {}
    for r, nm in ((0, "一次を基準"), (2, "三次を基準")):
        keep = [j for j in range(3) if j != r]
        b, s = hc1(P[:, keep], y)
        k = keep.index(1) + 1
        res[nm] = [float(b[k] * 0.01), float(s[k] * 0.01)]
    Z = ilr_pivot(P, 1)
    b, s = hc1(Z, y)
    f = np.sqrt(2 / 3) * np.log(1.1)
    res["ilr（二次÷ほか）"] = [float(b[1] * f), float(s[1] * f)]
    return res


summary["D_census3_pref"] = part_A_census(p26)
summary["D_census3_muni"] = part_A_census(d26)
# 都道府県の構成比（3分類）を図用に
pd.DataFrame(close(p26[["sec1", "sec2", "sec3"]].values.astype(float)), columns=["一次", "二次", "三次"]).to_csv(
    RES / "census3_pref.csv", index=False)
pd.DataFrame(close(d26[["sec1", "sec2", "sec3"]].values.astype(float)), columns=["一次", "二次", "三次"]).to_csv(
    RES / "census3_muni.csv", index=False)

# 平均的な構成（6分類）
summary["excluded_munis"] = EXCLUDED
summary["mean_share_pref_G6"] = dict(zip(G6, close(counts(p26, G6)).mean(0).round(4).tolist()))
summary["mean_share_muni_G6"] = dict(zip(G6, close(counts(d26, G6)).mean(0).round(4).tolist()))
summary["zero_cells_muni_G6"] = int((counts(d26, G6) == 0).sum())
summary["zero_cells_muni_G10"] = int((counts(d26, G10) == 0).sum())


def conv(o):
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=conv)
print(json.dumps(summary, ensure_ascii=False, indent=1, default=conv))
