"""差の差の推定をまとめた関数。データは「単位・時点・結果・処置の開始時点 g（処置されない単位は inf）」の縦長の表。
外部の差の差のパッケージは使わず、numpy と pandas だけで書いている（中身が見えるように）。"""
import numpy as np
import pandas as pd


def twoway_demean(x, unit, time, iters=500, tol=1e-12):
    """単位と時点の平均を交互に引く（つり合いのとれたパネルなら数回で収束）。"""
    s = pd.Series(np.asarray(x, float))
    u, t = pd.Series(np.asarray(unit)), pd.Series(np.asarray(time))
    for _ in range(iters):
        old = s.copy()
        s = s - s.groupby(u).transform("mean")
        s = s - s.groupby(t).transform("mean")
        if np.max(np.abs(s - old)) < tol:
            break
    return s.to_numpy()


def twfe_static(df, y="y"):
    """y = 単位の効果 + 時点の効果 + β·D の β（D は処置後なら1）。"""
    D = (df["t"] >= df["g"]).astype(float).to_numpy()
    yr = twoway_demean(df[y], df["unit"], df["t"])
    Dr = twoway_demean(D, df["unit"], df["t"])
    return float(Dr @ yr / (Dr @ Dr)), Dr, D


def cell_weights(df):
    """TWFE の β が、処置された単位×時点ごとの効果 τ_it にどんな重みをかけた平均になっているか（de Chaisemartin–D'Haultfœuille）。"""
    _, Dr, D = twfe_static(df)
    tr = D == 1
    w = Dr[tr] / Dr[tr].sum()
    return df.loc[tr].assign(w=w)


def att_gt(df, y="y", control="never"):
    """Callaway–Sant'Anna の ATT(g,t)。共変量なし・平均の差。処置後は g−1 を基準、処置前は1期前を基準（varying base）。"""
    W = df.pivot(index="unit", columns="t", values=y)
    G = df.drop_duplicates("unit").set_index("unit")["g"].reindex(W.index).to_numpy(float)
    ts = list(W.columns)
    col = {t: j for j, t in enumerate(ts)}
    A = W.to_numpy(float)
    out = []
    for g in sorted(np.unique(G[np.isfinite(G)])):
        tr = G == g
        for t in ts[1:]:
            base = g - 1 if t >= g else t - 1
            if base not in col:
                continue
            if control == "never":
                c = ~np.isfinite(G)
            else:
                c = (G > max(t, base)) & ~tr
            if c.sum() == 0:
                continue
            att = (A[tr, col[t]] - A[tr, col[base]]).mean() - (A[c, col[t]] - A[c, col[base]]).mean()
            out.append({"g": g, "t": t, "e": t - g, "att": att, "n_t": int(tr.sum())})
    return pd.DataFrame(out)


def cs_aggregate(a):
    """処置後の ATT(g,t) を、単位の数で重みをつけて1つにまとめる（simple）。相対時点ごとの平均（event study）も返す。"""
    post = a[a.e >= 0]
    simple = float(np.average(post.att, weights=post.n_t))
    ev = a.groupby("e").apply(lambda d: np.average(d.att, weights=d.n_t), include_groups=False)
    return simple, ev


def sun_abraham(df, y="y"):
    """Sun–Abraham：処置の開始時点×相対時点のダミー（−1 を基準、比較は処置されない単位）で回帰し、
    単位の数で重みをつけて相対時点ごと・全体にまとめる。"""
    d = df.copy()
    cols, meta = [], []
    gs = sorted(d.loc[np.isfinite(d.g), "g"].unique())
    for g in gs:
        for e in sorted((d.loc[d.g == g, "t"] - g).unique()):
            if e == -1:
                continue
            c = f"c{int(g)}_{int(e)}"
            d[c] = ((d.g == g) & (d.t - g == e)).astype(float)
            cols.append(c)
            meta.append((g, int(e)))
    yr = twoway_demean(d[y], d["unit"], d["t"])
    X = np.column_stack([twoway_demean(d[c], d["unit"], d["t"]) for c in cols])
    b = np.linalg.lstsq(X, yr, rcond=None)[0]
    n_g = d.drop_duplicates("unit").groupby("g").size()
    res = pd.DataFrame(meta, columns=["g", "e"]).assign(b=b, n=lambda z: z.g.map(n_g))
    ev = res.groupby("e").apply(lambda z: np.average(z.b, weights=z.n), include_groups=False)
    post = res[res.e >= 0]
    return float(np.average(post.b, weights=post.n)), ev


def twfe_event_trimmed(df, y="y", lo=-5, hi=5):
    """よくある書き方：相対時点 lo〜hi のダミーだけ入れ（−1 を基準）、それより外は基準と同じ扱いにする TWFE。"""
    d = df.copy()
    rel = d.t - d.g
    cols = []
    for e in range(lo, hi + 1):
        if e == -1:
            continue
        c = f"e{e}"
        d[c] = (rel == e).astype(float)
        cols.append((e, c))
    yr = twoway_demean(d[y], d["unit"], d["t"])
    X = np.column_stack([twoway_demean(d[c], d["unit"], d["t"]) for _, c in cols])
    b = np.linalg.lstsq(X, yr, rcond=None)[0]
    return pd.Series(b, index=[e for e, _ in cols])


def bacon(df, y="y"):
    """Goodman-Bacon の分解（つり合いのとれたパネル・処置されない単位あり）。2×2 の差の差と、その重みを返す。"""
    ts = sorted(df.t.unique())
    T = len(ts)
    gmap = df.drop_duplicates("unit").set_index("unit")["g"]
    N = len(gmap)
    _, Dr, _ = twfe_static(df)
    VD = float((Dr ** 2).mean())
    W = df.pivot(index="unit", columns="t", values=y)
    cohorts = sorted(gmap[np.isfinite(gmap)].unique())
    groups = {g: gmap.index[gmap == g] for g in cohorts}
    U = gmap.index[~np.isfinite(gmap)]
    n = {g: len(v) / N for g, v in groups.items()}
    nU = len(U) / N
    Dbar = {g: np.mean([t >= g for t in ts]) for g in cohorts}

    def did22(tr, ct, pre, post):
        return (W.loc[tr, post].to_numpy().mean() - W.loc[tr, pre].to_numpy().mean()) - \
               (W.loc[ct, post].to_numpy().mean() - W.loc[ct, pre].to_numpy().mean())

    rows = []
    for g in cohorts:
        if nU > 0:
            nk = n[g] / (n[g] + nU)
            s = (n[g] + nU) ** 2 * nk * (1 - nk) * Dbar[g] * (1 - Dbar[g]) / VD
            rows.append({"kind": "処置 vs 処置されない", "treat": g, "control": "なし", "w": s,
                         "est": did22(groups[g], U, [t for t in ts if t < g], [t for t in ts if t >= g])})
    for i, k in enumerate(cohorts):
        for l in cohorts[i + 1:]:
            nkl = n[k] / (n[k] + n[l])
            sk = ((n[k] + n[l]) * (1 - Dbar[l])) ** 2 * nkl * (1 - nkl) * ((Dbar[k] - Dbar[l]) / (1 - Dbar[l])) * ((1 - Dbar[k]) / (1 - Dbar[l])) / VD
            sl = ((n[k] + n[l]) * Dbar[k]) ** 2 * nkl * (1 - nkl) * (Dbar[l] / Dbar[k]) * ((Dbar[k] - Dbar[l]) / Dbar[k]) / VD
            rows.append({"kind": "早い組 vs まだの組", "treat": k, "control": l, "w": sk,
                         "est": did22(groups[k], groups[l], [t for t in ts if t < k], [t for t in ts if k <= t < l])})
            rows.append({"kind": "遅い組 vs すでに処置された組", "treat": l, "control": k, "w": sl,
                         "est": did22(groups[l], groups[k], [t for t in ts if k <= t < l], [t for t in ts if t >= l])})
    return pd.DataFrame(rows)
