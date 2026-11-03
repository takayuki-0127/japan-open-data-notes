"""F155 マルチバース分析：分析の選択肢をすべて組み合わせて推定し、答えの分布を見る。
問いA：最低賃金の引き上げで、bite の高い県の就業率は下がったか（F01 のデータ）
問いB：保育所に通う子どもが多い（増えた）市区町村ほど、出生率は高い（上がった）か（F100 のデータ）
使い方：python src/03_分析.py   （結果は results/ に保存。全体で 10〜20 分）"""
import itertools, json, time, sys
import numpy as np
import pandas as pd
from scipy import stats
from common import (DATA, RES, SEED, REGION, HIT3, fwl_beta_cluster, ols_hc1, shapley_r2, summarize)

P_PERM = int(__import__("os").environ.get("P", 500))   # 問いA の並べ替えの回数
B_BOOT = int(__import__("os").environ.get("B", 500))   # 問いB のブートストラップの回数
rng = np.random.default_rng(SEED)
LOG = open(RES / "run_log.txt", "w")


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s); LOG.write(s + "\n"); LOG.flush()


# =====================================================================
# 問いA：最低賃金（都道府県×年のパネル、差の差）
# =====================================================================
A = pd.read_csv(DATA / "f01_panel.csv")
A["region"] = A.code.map(REGION)
POP15 = A[A.year == 2015].set_index("code").pop15
BITE = A.groupby("code").bite.first()

A_DIMS = {
    "処置の定義": ["中央値で2分", "上下3分の1", "連続（bite）"],
    "期間の始まり": [2008, 2012],
    "期間の終わり": ["2019年まで", "2022年まで", "2025年まで", "2025年まで（2020〜22年を除く）"],
    "追加の条件": ["なし", "地方×年", "県別の傾き"],
    "対象": ["47県", "被災3県を除く"],
    "重み": ["なし", "15歳以上人口"],
}
A_DEFAULT = {"処置の定義": "中央値で2分", "期間の始まり": 2008, "期間の終わり": "2019年まで",
             "追加の条件": "なし", "対象": "47県", "重み": "なし"}
A_OUT = ["emp_rate", "unemp_rate"]  # 就業率（主）、完全失業率（確認）


def a_frame(start, end, sample):
    endy = 2019 if end == "2019年まで" else 2022 if end == "2022年まで" else 2025
    d = A[(A.year >= start) & (A.year <= endy)]
    if "除く" in end:
        d = d[~d.year.between(2020, 2022)]
    if sample == "被災3県を除く":
        d = d[~d.code.isin(HIT3)]
    return d.reset_index(drop=True)


def a_X(d, ctrl):
    """固定効果と追加の条件の行列（定数なし。県ダミーはすべて入れ、年は最初を落とす）"""
    cols = [pd.get_dummies(d.code, prefix="p").astype(float)]
    if ctrl == "地方×年":
        ry = pd.get_dummies(d.region + "_" + d.year.astype(str)).astype(float)
        cols.append(ry)
    else:
        cols.append(pd.get_dummies(d.year, prefix="y", drop_first=True).astype(float))
    if ctrl == "県別の傾き":
        tr = pd.get_dummies(d.code, prefix="t").astype(float).mul(d.year - 2015, axis=0)
        cols.append(tr)
    return pd.concat(cols, axis=1).values


def basis(X, w):
    """重み付きの列空間の正規直交基底（ランク落ちに強いよう SVD で）"""
    Xs = X * np.sqrt(w)[:, None]
    U, s, _ = np.linalg.svd(Xs, full_matrices=False)
    r = int(np.sum(s > s[0] * 1e-10))
    return U[:, :r], r


def resid(U, M, w):
    sw = np.sqrt(w)[:, None] if M.ndim == 2 else np.sqrt(w)
    Ms = M * sw
    return (Ms - U @ (U.T @ Ms)) / sw


def a_treat(bite_pref, codes_in_sample):
    """県ごとの bite から、3つの処置の定義に使う値をつくる"""
    b = bite_pref.loc[codes_in_sample]
    med = np.median(bite_pref.values)  # 中央値は47県で固定（F01 と同じ）
    high = (bite_pref > med).astype(float)
    q1, q2 = np.quantile(bite_pref.values, [1 / 3, 2 / 3])
    tert = pd.Series(np.where(bite_pref > q2, 1.0, np.where(bite_pref <= q1, 0.0, np.nan)), index=bite_pref.index)
    sd = b.std(ddof=1)
    z = (bite_pref - b.mean()) / sd
    # 2分・3分の1の係数を「bite 1標準偏差あたり」に直す倍率
    hs = high.loc[codes_in_sample]
    sc_bin = sd / (b[hs == 1].mean() - b[hs == 0].mean())
    ts = tert.loc[codes_in_sample]
    sc_ter = sd / (b[ts == 1].mean() - b[ts == 0].mean())
    return high, tert, z, sc_bin, sc_ter


def run_A():
    t0 = time.time()
    rows = []
    perm_est = {o: [] for o in A_OUT}; perm_lo = {o: [] for o in A_OUT}; perm_hi = {o: [] for o in A_OUT}
    codes47 = BITE.index.values
    perms = [rng.permutation(len(codes47)) for _ in range(P_PERM)]
    for start, end, ctrl, sample, wt in itertools.product(A_DIMS["期間の始まり"], A_DIMS["期間の終わり"],
                                                          A_DIMS["追加の条件"], A_DIMS["対象"], A_DIMS["重み"]):
        d = a_frame(start, end, sample)
        X = a_X(d, ctrl)
        w = d.code.map(POP15).values / POP15.mean() if wt == "15歳以上人口" else np.ones(len(d))
        post = (d.year >= 2016).values.astype(float)
        Y = d[A_OUT].values
        codes_s = np.sort(d.code.unique())
        grp = d.code.values
        U, r = basis(X, w)
        Yt = resid(U, Y, w)
        # 県の行列（クラスタごとの合計を速くとる）
        G = pd.get_dummies(grp).astype(float).values.T  # G×n
        # 観測された値と、並べ替えた bite（観測は先頭）
        bite_sets = [BITE] + [pd.Series(BITE.values[p], index=codes47) for p in perms]
        for kind in A_DIMS["処置の定義"]:
            ests = {o: np.empty(len(bite_sets)) for o in A_OUT}
            ses = {o: np.empty(len(bite_sets)) for o in A_OUT}
            Gs = None
            if kind != "上下3分の1":
                Dm = np.empty((len(d), len(bite_sets))); scs = np.empty(len(bite_sets))
                for i, bs in enumerate(bite_sets):
                    high, tert, z, sc_bin, sc_ter = a_treat(bs, codes_s)
                    if kind == "中央値で2分":
                        Dm[:, i] = d.code.map(high).values * post; scs[i] = sc_bin
                    else:
                        Dm[:, i] = d.code.map(z).values * post; scs[i] = 1.0
                Dt = resid(U, Dm, w)
                sxx = np.sum(w[:, None] * Dt * Dt, axis=0)
                nG = G.shape[0]; n = len(d)
                c = nG / (nG - 1) * (n - 1) / max(n - r - 1, 1)
                for j, o in enumerate(A_OUT):
                    yt = Yt[:, j][:, None]
                    b = np.sum(w[:, None] * Dt * yt, axis=0) / sxx
                    e = yt - b * Dt
                    s = G @ (w[:, None] * Dt * e)
                    se = np.sqrt(c * np.sum(s ** 2, axis=0)) / sxx
                    ests[o] = b * scs; ses[o] = se * scs
                Gn = nG
            else:
                for i, bs in enumerate(bite_sets):
                    high, tert, z, sc_bin, sc_ter = a_treat(bs, codes_s)
                    keep = d.code.map(tert).notna().values
                    dd = d[keep]
                    Xk = X[keep]; wk = w[keep]
                    Uk, rk = basis(Xk, wk)
                    dk = dd.code.map(tert).values * post[keep]
                    dkt = resid(Uk, dk, wk)
                    Ykt = resid(Uk, Y[keep], wk)
                    for j, o in enumerate(A_OUT):
                        b, se, Gn = fwl_beta_cluster(Ykt[:, j], dkt, wk, dd.code.values, rk + 1)
                        ests[o][i] = b * sc_ter; ses[o][i] = se * sc_ter
            tcrit = stats.t.ppf(0.975, Gn - 1)
            for o in A_OUT:
                b0, se0 = ests[o][0], ses[o][0]
                rows.append(dict(outcome=o, 処置の定義=kind, 期間の始まり=start, 期間の終わり=end, 追加の条件=ctrl,
                                 対象=sample, 重み=wt, est=b0, se=se0, lo=b0 - tcrit * se0, hi=b0 + tcrit * se0,
                                 n=len(d), G=Gn))
                perm_est[o].append(ests[o][1:]); perm_lo[o].append(ests[o][1:] - tcrit * ses[o][1:])
                perm_hi[o].append(ests[o][1:] + tcrit * ses[o][1:])
        log(f"A {start} {end} {ctrl} {sample} {wt}: {time.time() - t0:.0f}s")
    spec = pd.DataFrame(rows)
    spec.to_csv(RES / "A_specifications.csv", index=False)
    null = {}
    for o in A_OUT:
        E = np.array(perm_est[o]).T; L = np.array(perm_lo[o]).T; H = np.array(perm_hi[o]).T  # P×specs
        null[o] = dict(median=np.median(E, axis=1), sig_pos=(L > 0).mean(axis=1), sig_neg=(H < 0).mean(axis=1))
    return spec, null


# =====================================================================
# 問いB：保育所と出生率（市区町村の横断、水準の比較と変化の比較）
# =====================================================================
def b_load(q, des):
    return pd.read_csv(DATA / f"f100_{q}_{des}.csv", dtype={"code": str}).set_index("code")


BASE_LEVEL = [c for c in b_load("q1", "level").columns if c not in ("name", "Y", "D", "D_fac")]
COV_GROUPS = [
    ("なし", []),
    ("人口・密度", ["log人口", "log人口密度"]),
    ("＋年齢・世帯", ["女性65歳以上の割合", "女性15〜64歳の割合", "核家族世帯の割合", "単独世帯の割合", "核家族以外の世帯の割合", "母子世帯の割合"]),
    ("＋産業・通勤・所得", ["第1次産業の割合", "第2次産業の割合", "第3次産業の割合", "女性の市外への通勤の割合", "昼夜間人口比率", "納税者1人あたり所得", "納税者の割合"]),
    ("＋財政・学歴・雇用", None),       # 2010年の地域の性格の残り全部
    ("＋前の値（変化の比較だけ）", None),  # 変化の比較で、もとの出生率・在所児・期間中の変化
]
B_DIMS = {
    "比べ方": ["水準", "変化"],
    "地域の条件": [g[0] for g in COV_GROUPS],
    "県の違い": ["除く（県ダミー）", "除かない"],
    "対象": ["全体", "人口1万人以上", "政令市・23区を除く"],
    "重み": ["なし", "人口"],
    "外れ値": ["そのまま", "上下1%を除く"],
    "処置の定義": ["連続（在所児）", "上下3分の1"],
}
B_DEFAULT = {"地域の条件": "＋財政・学歴・雇用", "県の違い": "除く（県ダミー）", "対象": "全体", "重み": "なし",
             "外れ値": "そのまま", "処置の定義": "連続（在所児）"}


def b_cov_cols(df, des, gi):
    cols = []
    for lab, add in COV_GROUPS[:gi + 1]:
        if add is None and lab.startswith("＋財政"):
            add = [c for c in BASE_LEVEL if c not in cols]
        if add is None and lab.startswith("＋前の値"):
            add = [c for c in df.columns if c not in BASE_LEVEL and c not in ("name", "Y", "D", "D_fac")]
        cols = list(dict.fromkeys(cols + add))
    return cols


def b_specs(q):
    """問いBの全指定を、行列と一緒に順に返す"""
    for des_lab, des in [("水準", "level"), ("変化", "change")]:
        df0 = b_load(q, des)
        ngroups = 6 if des == "change" else 5
        for gi in range(ngroups):
            cols = b_cov_cols(df0, des, gi)
            for pref, sample, wt, outl, kind in itertools.product(B_DIMS["県の違い"], B_DIMS["対象"], B_DIMS["重み"],
                                                                   B_DIMS["外れ値"], B_DIMS["処置の定義"]):
                df = df0[["Y", "D"] + cols].dropna().copy()
                if sample == "人口1万人以上":
                    df = df[np.exp(df0.loc[df.index, "log人口"]) >= 10000]
                elif sample == "政令市・23区を除く":
                    idx = df.index
                    df = df[~((idx.str[:2] == "13") & (idx.str[2] == "1")) & ~(idx.str[2:] == "100")]
                if outl == "上下1%を除く":
                    keep = np.ones(len(df), bool)
                    for v in ("Y", "D"):
                        lo_, hi_ = df[v].quantile([0.01, 0.99])
                        keep &= df[v].between(lo_, hi_).values
                    df = df[keep]
                if kind == "上下3分の1":
                    q1, q2 = df.D.quantile([1 / 3, 2 / 3])
                    t = np.where(df.D > q2, 1.0, np.where(df.D <= q1, 0.0, np.nan))
                    dfk = df[~np.isnan(t)]
                    dreg = t[~np.isnan(t)]
                    scale = 10.0 / (dfk.D[dreg == 1].mean() - dfk.D[dreg == 0].mean())
                    df = dfk
                else:
                    dreg = df.D.values / 10.0
                    scale = 1.0
                Z = [np.ones(len(df)), dreg]
                if cols:
                    Xc = df[cols].values
                    sdv = Xc.std(0)
                    Xc = (Xc[:, sdv > 0] - Xc[:, sdv > 0].mean(0)) / sdv[sdv > 0]  # 対象で値が変わらない列は落とす
                    Z.append(Xc)
                if pref == "除く（県ダミー）":
                    pdm = pd.get_dummies(pd.Series(df.index.str[:2], index=df.index), drop_first=True).astype(float).values
                    Z.append(pdm)
                X = np.column_stack(Z)
                popw = np.exp(b_load(q, des).loc[df.index, "log人口"].values)
                w = popw / popw.mean() if wt == "人口" else None
                yield dict(比べ方=des_lab, 地域の条件=COV_GROUPS[gi][0], 県の違い=pref, 対象=sample, 重み=wt,
                           外れ値=outl, 処置の定義=kind), X, df.Y.values, w, scale, df.index.values


def run_B(q, boot=True):
    t0 = time.time()
    rows = []
    universe = None
    draws = None
    null_E, null_L, null_H = [], [], []
    for meta, X, y, w, scale, codes in b_specs(q):
        b, se = ols_hc1(X, y, w, j=1)
        n, k = X.shape
        tcrit = stats.t.ppf(0.975, n - k)
        rows.append(dict(**meta, est=b * scale, se=se * scale, lo=(b - tcrit * se) * scale,
                         hi=(b + tcrit * se) * scale, n=n, k=k))
        if not boot:
            continue
        if universe is None:
            universe = np.array(sorted(set(b_load(q, "level").index) | set(b_load(q, "change").index)))
            draws = rng.integers(0, len(universe), size=(B_BOOT, len(universe)))
            counts_all = np.stack([np.bincount(dr, minlength=len(universe)) for dr in draws])  # B×N
            pos_of = {c: i for i, c in enumerate(universe)}
            run_B.counts = counts_all; run_B.pos_of = pos_of
        # 帰無仮説（効果0）を課したブートストラップ：y* = y − b̂·d、市区町村を復元抽出
        ystar = y - b * X[:, 1]
        cidx = np.array([run_B.pos_of[c] for c in codes])
        C = run_B.counts[:, cidx].astype(float)  # B×n（各市区町村が何回引かれたか）
        wb = C * (w if w is not None else 1.0)
        # 各回の重み付き正規方程式
        Kmat = (X[:, :, None] * X[:, None, :]).reshape(len(X), k * k)  # 各市区町村の x x'（行列積で速く足す）
        XtX = (wb @ Kmat).reshape(-1, k, k)
        Xty = wb @ (X * ystar[:, None])
        reg = 1e-8 * np.eye(k)
        beta = np.linalg.solve(XtX + reg, Xty[..., None])[..., 0]
        e = ystar[None, :] - beta @ X.T  # B×n
        inv = np.linalg.inv(XtX + reg)
        # HC1：Σ c w² e² x x'（同じ市区町村が c 回引かれた分を重みで表す）
        ww = C * (w if w is not None else 1.0) ** 2
        meat = ((ww * e ** 2) @ Kmat).reshape(-1, k, k)
        nb = C.sum(1)
        V11 = np.einsum("bi,bij,bj->b", inv[:, 1, :], meat, inv[:, :, 1]) * nb / (nb - k)
        seb = np.sqrt(V11)
        null_E.append(beta[:, 1] * scale)
        null_L.append((beta[:, 1] - tcrit * seb) * scale)
        null_H.append((beta[:, 1] + tcrit * seb) * scale)
        if len(rows) % 48 == 0:
            log(f"B {q} {len(rows)} specs: {time.time() - t0:.0f}s")
    spec = pd.DataFrame(rows)
    null = None
    if boot:
        E = np.array(null_E).T; L = np.array(null_L).T; H = np.array(null_H).T
        null = dict(median=np.median(E, axis=1), sig_pos=(L > 0).mean(axis=1), sig_neg=(H < 0).mean(axis=1))
    return spec, null


# =====================================================================
# まとめ
# =====================================================================
def joint_test(spec, null):
    obs_med = float(spec.est.median())
    obs_pos = float((spec.lo > 0).mean()); obs_neg = float((spec.hi < 0).mean())
    return dict(observed_median=obs_med, observed_sig_pos=obs_pos, observed_sig_neg=obs_neg,
                p_median_two_sided=float(np.mean(np.abs(null["median"]) >= abs(obs_med))),
                p_sig_dominant=float(np.mean(
                    (null["sig_pos"] if obs_med > 0 else null["sig_neg"]) >= (obs_pos if obs_med > 0 else obs_neg))),
                null_median_p025=float(np.quantile(null["median"], 0.025)),
                null_median_p975=float(np.quantile(null["median"], 0.975)),
                null_sig_any_mean=float(np.mean(null["sig_pos"] + null["sig_neg"])),
                n_draws=int(len(null["median"])))


def leave_fixed(spec, dims, default):
    """1つの選択肢を基本に固定したとき、残りの推定値の幅（5〜95%）がどれだけ縮むか"""
    full = summarize(spec.est, spec.lo, spec.hi)
    w_full = full["p95"] - full["p05"]
    out = {}
    for d_, v in default.items():
        s = spec[spec[d_] == v]
        sm_ = summarize(s.est, s.lo, s.hi)
        out[d_] = dict(fixed_to=str(v), n=sm_["n"], p05=sm_["p05"], p95=sm_["p95"],
                       width=sm_["p95"] - sm_["p05"], shrink=1 - (sm_["p95"] - sm_["p05"]) / w_full)
    return dict(full_width=w_full, by_dim=out)


def weighting(spec, plausible_mask, per_design=None):
    out = {"等しい重み": summarize(spec.est, spec.lo, spec.hi)}
    if per_design is not None:
        cnt = spec[per_design].map(spec[per_design].value_counts())
        out["比べ方ごとに等しい重み"] = summarize(spec.est, spec.lo, spec.hi, 1.0 / cnt)
    out["精度の重み（1/SE²）"] = summarize(spec.est, spec.lo, spec.hi, 1.0 / spec.se ** 2)
    s = spec[plausible_mask]
    out["妥当と考えた指定だけ"] = summarize(s.est, s.lo, s.hi)
    return out


if __name__ == "__main__":
    R = {}
    # ---- 問いA
    specA, nullA = run_A()
    R["A"] = {}
    for o in A_OUT:
        s = specA[specA.outcome == o].reset_index(drop=True)
        dims = {d_: s[d_].astype(str).values for d_ in A_DIMS}
        base = s
        for k_, v in A_DEFAULT.items():
            base = base[base[k_] == v]
        R["A"][o] = dict(
            summary=summarize(s.est, s.lo, s.hi),
            baseline=base.iloc[0][["est", "se", "lo", "hi"]].astype(float).to_dict(),
            shapley=shapley_r2(s.est, dims),
            joint=joint_test(s, nullA[o]),
            leave_fixed=leave_fixed(s, A_DIMS, A_DEFAULT),
            weighting=weighting(s, ~s["期間の終わり"].isin(["2022年まで", "2025年まで"])),
            by_choice={d_: s.groupby(d_).est.median().to_dict() for d_ in A_DIMS},
        )
        np.save(RES / f"A_null_median_{o}.npy", nullA[o]["median"])
    log(json.dumps(R["A"]["emp_rate"]["joint"], ensure_ascii=False))
    # ---- 問いB（出生率、帰無ブートストラップあり）と確認（女性の労働力率）
    specB, nullB = run_B("q1", boot=True)
    specB.to_csv(RES / "B_specifications.csv", index=False)
    np.save(RES / "B_null_median_tfr.npy", nullB["median"])
    specB2, _ = run_B("q2", boot=False)
    specB2.to_csv(RES / "B2_specifications_lfpr.csv", index=False)
    R["B"] = {}
    for lab, s in [("tfr", specB), ("lfpr", specB2)]:
        dims = {d_: s[d_].astype(str).values for d_ in B_DIMS}
        r = dict(summary=summarize(s.est, s.lo, s.hi), shapley=shapley_r2(s.est, dims),
                 weighting=weighting(s, ~s["地域の条件"].isin(["なし", "人口・密度"]), per_design="比べ方"),
                 by_choice={d_: s.groupby(d_).est.median().to_dict() for d_ in B_DIMS})
        for des in ["水準", "変化"]:
            sd_ = s[s["比べ方"] == des]
            r[f"summary_{des}"] = summarize(sd_.est, sd_.lo, sd_.hi)
            base = sd_
            for k_, v in B_DEFAULT.items():
                vv = "＋前の値（変化の比較だけ）" if (k_ == "地域の条件" and des == "変化") else v
                base = base[base[k_] == vv]
            r[f"baseline_{des}"] = base.iloc[0][["est", "se", "lo", "hi"]].astype(float).to_dict()
            dd = {d_: sd_[d_].astype(str).values for d_ in B_DIMS if d_ != "比べ方"}
            r[f"shapley_{des}"] = shapley_r2(sd_.est, dd)
            dflt = dict(B_DEFAULT)
            if des == "変化":
                dflt["地域の条件"] = "＋前の値（変化の比較だけ）"
            r[f"leave_fixed_{des}"] = leave_fixed(sd_, {k_: None for k_ in dflt}, dflt)
        if lab == "tfr":
            r["joint"] = joint_test(s, nullB)
        R["B"][lab] = r
    log(json.dumps(R["B"]["tfr"]["joint"], ensure_ascii=False))

    def conv(o):
        if isinstance(o, dict):
            return {str(k): conv(v) for k, v in o.items()}
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        return o
    json.dump(conv(R), open(RES / "results.json", "w"), ensure_ascii=False, indent=1)
    log("done")
