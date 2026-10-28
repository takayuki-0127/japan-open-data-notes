"""年齢・時代・コホート（APC）分解。

モデル： log(初婚率) = μ + 年齢効果 + 時代効果 + コホート効果   （効果は合計0の表し方）
本体は国勢調査の未婚割合（ロジット）。年齢は10歳階級（5歳階級2つの単純平均）、時代は10年おき、
コホート = 調査年 − 年齢階級の下端（生まれ年の目安、10年おき）。
※5歳階級×10年おきのままだと、コホートが「奇数組」と「偶数組」に分かれて、もう1つ識別できない方向が生まれる（2つの組の水準差）。
  そのため年齢を10歳階級にそろえる（頑健性で、5歳階級のままコホートを10年でまとめる方法も試す）。
「年齢 + コホート = 時代」が成り立つため、直線の傾きを年齢・コホートに足して時代から引いても当てはまりは同じになる。
この1方向の自由度（t）をどう決めるかで、時代とコホートの「分け方」が変わる。
"""
import json
import numpy as np
import pandas as pd
from common import DATA, RES, AGES, PERIODS, SEED

AGES10_UM = ["20-29", "30-39", "40-49", "50-59"]   # 本体（未婚割合）
AGES10_FM = ["20-29", "30-39", "40-49"]            # 初婚率

def to10(d, val):
    """5歳階級2つを単純平均して10歳階級にする（人口の重みは使わない近似）"""
    d = d.copy()
    lo = d.age.str.split("-").str[0].astype(int)
    d["age"] = (lo // 10 * 10).astype(str) + "-" + (lo // 10 * 10 + 9).astype(str)
    g = d.groupby(["sex", "age", "year"])[val].agg(["mean", "count"]).reset_index()
    g = g[g["count"] == 2].rename(columns={"mean": val}).drop(columns="count")
    return g

def design(df, cohort_bin=None):
    A = sorted(df.age.unique(), key=lambda s: int(s.split("-")[0]))
    P = sorted(df.year.unique())
    df = df.copy()
    df["alow"] = df.age.str.split("-").str[0].astype(int)
    df["coh"] = df.year - df.alow
    if cohort_bin:
        df["coh"] = (df.coh // cohort_bin) * cohort_bin
    C = sorted(df.coh.unique())
    def eff(vals, levels):  # 合計0の表し方（最後の水準 = −他の合計）
        X = np.zeros((len(vals), len(levels) - 1))
        for i, v in enumerate(vals):
            k = levels.index(v)
            if k < len(levels) - 1:
                X[i, k] = 1
            else:
                X[i, :] = -1
        return X
    X = np.hstack([np.ones((len(df), 1)), eff(list(df.age), A), eff(list(df.year), P), eff(list(df.coh), C)])
    return df, X, A, P, C

def unpack(b, A, P, C):
    i = 1
    a = np.append(b[i:i + len(A) - 1], -b[i:i + len(A) - 1].sum()); i += len(A) - 1
    p = np.append(b[i:i + len(P) - 1], -b[i:i + len(P) - 1].sum()); i += len(P) - 1
    c = np.append(b[i:i + len(C) - 1], -b[i:i + len(C) - 1].sum())
    return a, p, c

def apc(df, y, cohort_bin=None):
    df, X, A, P, C = design(df, cohort_bin)
    yy = df[y].values
    b = np.linalg.pinv(X) @ yy           # 内在推定量（IE）：最小ノルム解
    a, p, c = unpack(b, A, P, C)
    rank = int(np.linalg.matrix_rank(X))
    fit = X @ b
    r2 = 1 - ((yy - fit) ** 2).sum() / ((yy - yy.mean()) ** 2).sum()
    ka = np.array([int(s.split("-")[0]) for s in A], float); ka -= ka.mean()
    kp = np.array(P, float); kp -= kp.mean()
    kc = np.array(C, float); kc -= kc.mean()
    return dict(A=A, P=P, C=C, a=a, p=p, c=c, ka=ka, kp=kp, kc=kc, r2=r2, n=len(df), rank=rank, ncol=X.shape[1])

def shift(m, t):
    """傾き t（10年あたり）を年齢・コホートに足し、時代から引く。当てはまりは変わらない。"""
    s = t / 10
    return m["a"] + s * m["ka"], m["p"] - s * m["kp"], m["c"] + s * m["kc"]

def slope(x, k):
    return float(np.polyfit(k, x, 1)[0] * 10)

def constraints(m):
    """よく使われる制約ごとの t（10年あたり）"""
    a0, p0, c0 = m["a"], m["p"], m["c"]
    out = {"IE（最小ノルム）": 0.0}
    # 時代の直線の傾きを0にする → すべての流れをコホートへ
    out["時代に直線の流れなし"] = slope(p0, m["kp"])
    # コホートの直線の傾きを0にする → すべての流れを時代へ
    out["コホートに直線の流れなし"] = -slope(c0, m["kc"])
    # 最初の2つの時代を等しい
    dp = m["kp"][1] - m["kp"][0]
    out["最初の2時代が等しい"] = (p0[1] - p0[0]) / dp * 10
    # 最初の2つのコホートを等しい
    dc = m["kc"][1] - m["kc"][0]
    out["最初の2コホートが等しい"] = -(c0[1] - c0[0]) / dc * 10
    return out

def curvature(x, k):
    """直線を引いた残り（どの制約でも同じ＝識別できる部分）"""
    return x - np.polyval(np.polyfit(k, x, 1), k)

def two_factor(df, y, cohort_bin=None):
    """年齢＋時代 と 年齢＋コホート の2要因モデルの当てはまり（これは識別できる比較）"""
    df, X, A, P, C = design(df, cohort_bin)
    yy = df[y].values
    nA, nP = len(A) - 1, len(P) - 1
    XA = X[:, :1 + nA]; XP = X[:, 1 + nA:1 + nA + nP]; XC = X[:, 1 + nA + nP:]
    res = {}
    for nm, M in {"年齢のみ": XA, "年齢＋時代": np.hstack([XA, XP]), "年齢＋コホート": np.hstack([XA, XC]), "年齢＋時代＋コホート": X}.items():
        b = np.linalg.lstsq(M, yy, rcond=None)[0]
        rss = ((yy - M @ b) ** 2).sum()
        k = np.linalg.matrix_rank(M)
        res[nm] = {"rss": float(rss), "r2": float(1 - rss / ((yy - yy.mean()) ** 2).sum()), "k": int(k),
                   "bic": float(len(yy) * np.log(rss / len(yy)) + k * np.log(len(yy)))}
    return res

def prep(kind, sex, ages=None, periods=PERIODS, ten=True):
    if kind == "fm":
        d = pd.read_csv(DATA / "first_marriage_rate.csv")
        if ten: d = to10(d, "first_marriage_rate")
        ages = ages or (AGES10_FM if ten else AGES)
        d = d[(d.sex == sex) & d.age.isin(ages) & d.year.isin(periods)].copy()
        d["y"] = np.log(d.first_marriage_rate)
    else:
        d = pd.read_csv(DATA / "unmarried_pct.csv")
        if ten: d = to10(d, "unmarried_pct")
        ages = ages or (AGES10_UM if ten else AGES + ["50-54", "55-59"])
        d = d[(d.sex == sex) & d.age.isin(ages) & d.year.isin(periods)].copy()
        p = d.unmarried_pct / 100
        d["y"] = np.log((1 - p) / p)            # 結婚したことがある側のロジット（大きいほど既婚が多い）
    return d

def summarize(m):
    cons = constraints(m)
    rows = []
    for nm, t in cons.items():
        a, p, c = shift(m, t)
        rows.append({"制約": nm, "t": t,
                     "時代の傾き": slope(p, m["kp"]), "コホートの傾き(10年)": slope(c, m["kc"]),
                     "時代の幅": float(p.max() - p.min()), "コホートの幅": float(c.max() - c.min()),
                     "1970→2020の時代効果": float(p[list(m["P"]).index(2020)] - p[list(m["P"]).index(1970)]) if 1970 in m["P"] and 2020 in m["P"] else np.nan})
    return pd.DataFrame(rows)

def one(kind, sex, ages=None, periods=PERIODS, ten=True, cohort_bin=None):
    d = prep(kind, sex, ages, periods, ten)
    m = apc(d, "y", cohort_bin)
    return d, m


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    out = {}
    curves = []
    for sex in ["女", "男"]:
        d, m = one("um", sex)
        cons = constraints(m)
        out[sex] = {"r2_apc": m["r2"], "n": m["n"], "rank": m["rank"], "ncol": m["ncol"], "constraints_t": cons,
                    "two_factor": two_factor(d, "y"),
                    "summary": summarize(m).to_dict(orient="records"),
                    "period_curv": dict(zip(map(str, m["P"]), curvature(m["p"], m["kp"]).round(4))),
                    "cohort_curv": dict(zip(map(str, m["C"]), curvature(m["c"], m["kc"]).round(4))),
                    "age_curv": dict(zip(m["A"], curvature(m["a"], m["ka"]).round(4)))}
        for nm, t in cons.items():
            a, p, c = shift(m, t)
            for lv, v in zip(m["A"], a): curves.append({"sex": sex, "constraint": nm, "kind": "age", "level": lv, "effect": v})
            for lv, v in zip(m["P"], p): curves.append({"sex": sex, "constraint": nm, "kind": "period", "level": lv, "effect": v})
            for lv, v in zip(m["C"], c): curves.append({"sex": sex, "constraint": nm, "kind": "cohort", "level": lv, "effect": v})
        # t を連続に動かしたときの、1970→2020 の時代効果と、1930→1980 年生まれのコホート効果（ロジット差）
        out[sex]["t_path"] = []
        C = list(m["C"])
        for t in np.linspace(-1.0, 1.0, 81):
            a, p, c = shift(m, t)
            out[sex]["t_path"].append({"t": float(t), "period_1970_2020": float(p[m["P"].index(2020)] - p[m["P"].index(1970)]),
                                       "cohort_1930_1980": float(c[C.index(1980)] - c[C.index(1930)])})
    pd.DataFrame(curves).to_csv(RES / "apc_effects_by_constraint.csv", index=False, encoding="utf-8-sig")

    # シミュレーション：本当は「コホートだけ」で動くデータを作り、制約を変えて当てはめる
    d, m = one("um", "女")
    dd, X, A, P, C = design(d)
    true_c = -0.4 * (np.array(C) - np.mean(C)) / 10         # 10年ごとに −0.4（ロジット）の純粋なコホートの流れ
    sim = dd[["age", "year"]].copy()
    sim["y"] = m["a"][[A.index(v) for v in dd.age]] + true_c[[C.index(v) for v in dd.coh]] + rng.normal(0, 0.03, len(dd))
    ms = apc(sim, "y")
    sim_rows = []
    for nm, t in constraints(ms).items():
        a, p, c = shift(ms, t)
        sim_rows.append({"制約": nm, "時代の傾き(10年)": slope(p, ms["kp"]), "コホートの傾き(10年)": slope(c, ms["kc"])})
    tfs = two_factor(sim, "y")
    out["simulation"] = {"true_cohort_slope_per10": -0.4, "true_period_slope_per10": 0.0, "rows": sim_rows,
                         "bic_age_period": tfs["年齢＋時代"]["bic"], "bic_age_cohort": tfs["年齢＋コホート"]["bic"]}

    # 頑健性
    rob = []
    settings = [("基本（女・未婚割合・1960–2020・20–59歳・10歳階級）", dict(kind="um", sex="女")),
                ("男", dict(kind="um", sex="男")),
                ("期間 1970–2020（女）", dict(kind="um", sex="女", periods=PERIODS[1:])),
                ("期間 1970–2020（男）", dict(kind="um", sex="男", periods=PERIODS[1:])),
                ("期間 1950–2020（女）", dict(kind="um", sex="女", periods=[1950] + PERIODS)),
                ("期間 1950–2020（男）", dict(kind="um", sex="男", periods=[1950] + PERIODS)),
                ("20–49歳（女）", dict(kind="um", sex="女", ages=AGES10_UM[:3])),
                ("20–49歳（男）", dict(kind="um", sex="男", ages=AGES10_UM[:3])),
                ("5歳階級のまま・コホートは10年でまとめる（女）", dict(kind="um", sex="女", ten=False, cohort_bin=10)),
                ("5歳階級のまま・コホートは10年でまとめる（男）", dict(kind="um", sex="男", ten=False, cohort_bin=10)),
                ("初婚率（人口動態）女 20–49歳", dict(kind="fm", sex="女")),
                ("初婚率（人口動態）男 20–49歳", dict(kind="fm", sex="男"))]
    for nm, kw in settings:
        cb = kw.get("cohort_bin")
        dz, mz = one(**kw)
        tf = two_factor(dz, "y", cb)
        row = {"設定": nm, "n": mz["n"], "階数/列": f"{mz['rank']}/{mz['ncol']}", "R2_APC": mz["r2"],
               "R2_年齢+時代": tf["年齢＋時代"]["r2"], "R2_年齢+コホート": tf["年齢＋コホート"]["r2"],
               "BIC_年齢+時代": tf["年齢＋時代"]["bic"], "BIC_年齢+コホート": tf["年齢＋コホート"]["bic"]}
        if mz["rank"] == mz["ncol"] - 1:      # 通常の APC（自由度1つ）のときだけ制約ごとの傾きを出す
            for nmc, t in constraints(mz).items():
                a, p, c = shift(mz, t)
                row[f"時代傾き_{nmc}"] = slope(p, mz["kp"])
            pc = curvature(mz["p"], mz["kp"])
            row["時代の曲率(1970)"] = float(pc[list(mz["P"]).index(1970)])
            row["時代の曲率(2020)"] = float(pc[list(mz["P"]).index(2020)])
        else:                                  # コホートをまとめて識別したとき：その解の時代の傾き
            b = np.linalg.lstsq(design(dz, cb)[1], dz["y"].values, rcond=None)[0]
            _, _, A_, P_, C_ = design(dz, cb)
            a, p, c = unpack(b, A_, P_, C_)
            kp = np.array(P_, float) - np.mean(P_)
            row["時代傾き_まとめて識別"] = slope(p, kp)
            row["コホート傾き_まとめて識別"] = slope(c, np.array(C_, float) - np.mean(C_))
        rob.append(row)
    pd.DataFrame(rob).to_csv(RES / "robustness.csv", index=False, encoding="utf-8-sig")

    # 記述：50歳時未婚割合を生まれ年で並べる
    r50 = pd.read_csv(DATA / "unmarried_at50.csv")
    r50["birth"] = r50.year - 50
    out["unmarried50"] = r50.pivot_table(index="birth", columns="sex", values="unmarried50_pct").reset_index().to_dict(orient="records")
    json.dump(out, open(RES / "results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=float)
    for sex in ["女", "男"]:
        print(sex, "R2", round(out[sex]["r2_apc"], 4), "rank", out[sex]["rank"], "/", out[sex]["ncol"])
        print(pd.DataFrame(out[sex]["summary"]).round(3).to_string())
        print({k: round(v["r2"], 4) for k, v in out[sex]["two_factor"].items()}, {k: round(v["bic"], 1) for k, v in out[sex]["two_factor"].items()})
        print("period curv", out[sex]["period_curv"])
        print("cohort curv", out[sex]["cohort_curv"])
    print(pd.DataFrame(out["simulation"]["rows"]).round(3), out["simulation"]["bic_age_period"], out["simulation"]["bic_age_cohort"])
    pd.set_option("display.width", 250)
    print(pd.DataFrame(rob).round(3).T.to_string())
