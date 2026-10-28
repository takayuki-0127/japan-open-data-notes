"""03 分析：市区町村の合計特殊出生率を、ふつうの機械学習とグラフニューラルネットワーク（GCN）で予測して比べる。

比べるモデル（入力はどれも同じ8指標。グラフを使うものは、テスト側の区域の「指標」は見るが「答え」は見ない）
  ridge      : 線形回帰（リッジ）
  lgbm       : LightGBM
  lgbm_nx    : LightGBM ＋ 隣の区域の指標の平均
  lgbm_ny    : LightGBM ＋ 隣の区域の指標の平均 ＋ 隣の「学習側の区域」の出生率の平均
  mlp        : 2層のニューラルネット（グラフなし。GCN の比較対象）
  gcn        : 2層の GCN（Kipf & Welling 2017）
  sage       : 2層の GraphSAGE 型（自分と隣の平均を別々の重みで足す）
検証の分け方：ランダム5分割（3回くり返し）と、都道府県ごとにまとめて5分割（空間ブロック）。
"""
import json
import sys
import time
import numpy as np
import pandas as pd
import torch
import warnings
warnings.filterwarnings("ignore")
import lightgbm as lgb
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, GroupKFold
from common import DATA, RES, SEED

torch.set_num_threads(2)
X = ["young_f", "income", "commute_out", "nursery", "tertiary", "density", "unmarried", "aged"]
QUICK = "quick" in sys.argv


def load(target="tfr"):
    df = pd.read_csv(DATA / "nodes.csv", dtype={"code": str, "pref": str})
    xs = [x for x in X if x != target]
    return df, xs


def edges(kind, df):
    n = len(df)
    if kind in ("adjacent", "knn6"):
        e = pd.read_csv(DATA / f"edges_{kind}.csv")
        return e.i.values, e.j.values
    w = pd.read_csv(DATA / "edges_commute_all.csv")
    if kind == "commute_top6":  # 各区域の通勤の多い相手6つ（両方向の合計）
        both = pd.concat([w[["i", "j", "n"]], w.rename(columns={"i": "j", "j": "i"})[["i", "j", "n"]]])
        top = both.sort_values("n", ascending=False).groupby("i").head(6)
        a, b = top.i.values, top.j.values
        return np.minimum(a, b), np.maximum(a, b)
    if kind == "commute_1pct":  # 小さいほうの人口の1%以上が行き来する組
        w = w[w.share >= 0.01]
        return w.i.values, w.j.values
    raise ValueError(kind)


def neighbor_lists(n, ei, ej):
    nb = [set() for _ in range(n)]
    for a, b in zip(ei, ej):
        if a != b:
            nb[a].add(b); nb[b].add(a)
    return [np.array(sorted(s), int) for s in nb]


def norm_adj(n, ei, ej, kind="gcn"):
    """GCN：D^-1/2 (A+I) D^-1/2、SAGE：隣の平均（自分を含まない）"""
    a = np.r_[ei, ej]; b = np.r_[ej, ei]
    m = a != b; a, b = a[m], b[m]
    if kind == "gcn":
        a = np.r_[a, np.arange(n)]; b = np.r_[b, np.arange(n)]
    A = torch.sparse_coo_tensor(np.vstack([a, b]), np.ones(len(a), np.float32), (n, n)).coalesce()
    deg = torch.sparse.sum(A, 1).to_dense()
    i, j = A.indices()
    if kind == "gcn":
        v = A.values() / torch.sqrt(deg[i] * deg[j])
    else:
        v = A.values() / deg[i].clamp(min=1)
    return torch.sparse_coo_tensor(A.indices(), v, (n, n)).coalesce()


class Net(torch.nn.Module):
    def __init__(self, d, kind, layers=2, h=32, p=0.3):
        super().__init__()
        self.kind, self.p = kind, p
        dims = [d] + [h] * (layers - 1) + [1]
        self.lin = torch.nn.ModuleList(torch.nn.Linear(dims[k], dims[k + 1]) for k in range(layers))
        if kind == "sage":
            self.lin_n = torch.nn.ModuleList(torch.nn.Linear(dims[k], dims[k + 1], bias=False) for k in range(layers))

    def forward(self, x, A):
        for k, lin in enumerate(self.lin):
            if k > 0:  # 入力の8指標には落とさず、隠れ層だけに dropout
                x = torch.nn.functional.dropout(x, self.p, self.training)
            if self.kind == "gcn":
                x = lin(torch.sparse.mm(A, x))
            elif self.kind == "sage":
                x = lin(x) + self.lin_n[k](torch.sparse.mm(A, x))
            else:
                x = lin(x)
            if k < len(self.lin) - 1:
                x = torch.relu(x)
        return x.squeeze(-1)


def fit_net(Xall, y, tr, te, A, kind, seed, layers=2, epochs=400):
    """学習側の1割を内側の検証に使い、検証の誤差がいちばん小さい回の重みで予測する"""
    torch.manual_seed(seed); rng = np.random.default_rng(seed)
    tr = np.array(tr); rng.shuffle(tr)
    nv = max(1, len(tr) // 10); va, tr2 = tr[:nv], tr[nv:]
    mu, sd = y[tr2].mean(), y[tr2].std()
    x = torch.tensor(Xall, dtype=torch.float32)
    t = torch.tensor((y - mu) / sd, dtype=torch.float32)
    net = Net(x.shape[1], kind, layers)
    opt = torch.optim.Adam(net.parameters(), lr=0.01, weight_decay=5e-4)
    best, state = np.inf, None
    for ep in range(epochs):
        net.train(); opt.zero_grad()
        out = net(x, A)
        loss = ((out[tr2] - t[tr2]) ** 2).mean()
        loss.backward(); opt.step()
        net.eval()
        with torch.no_grad():
            o = net(x, A)
            v = ((o[va] - t[va]) ** 2).mean().item()
        if v < best:
            best, state = v, o.detach().numpy().copy()
    return state[te] * sd + mu


def nb_mean(M, nbs, mask=None):
    out = np.full(M.shape, np.nan)
    for i, nb in enumerate(nbs):
        if mask is not None:
            nb = nb[mask[nb]]
        if len(nb):
            out[i] = M[nb].mean(axis=0)
    return out


def fit_lgbm(F, y, tr, te, seed):
    m = lgb.LGBMRegressor(n_estimators=400, learning_rate=0.03, num_leaves=15, min_child_samples=20,
                          subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=seed, verbose=-1)
    m.fit(F[tr], y[tr])
    return m.predict(F[te])


def splits(df, scheme, rep):
    n = len(df)
    if scheme == "random":
        return list(KFold(5, shuffle=True, random_state=SEED + rep).split(np.arange(n)))
    # 都道府県をまとめて5つに分ける（くり返しごとに県の並びを入れ替える）
    prefs = df["pref"].values
    up = np.unique(prefs); rng = np.random.default_rng(SEED + rep); perm = rng.permutation(len(up))
    gmap = {p: perm[k] % 5 for k, p in enumerate(up)}
    g = np.array([gmap[p] for p in prefs])
    return [(np.where(g != k)[0], np.where(g == k)[0]) for k in range(5) if (g == k).any()]


def run(df, xs, target, graph, scheme, reps, models, layers=2, tag="", rep0=0):
    n = len(df)
    Xr = df[xs].values.astype(float)
    Xs = (Xr - Xr.mean(0)) / Xr.std(0)
    y = df[target].values.astype(float)
    ei, ej = edges(graph, df)
    nbs = neighbor_lists(n, ei, ej)
    A_g, A_s = norm_adj(n, ei, ej, "gcn"), norm_adj(n, ei, ej, "sage")
    NX = nb_mean(Xs, nbs)
    NX = np.where(np.isnan(NX), Xs, NX)  # 隣がない区域は自分の値
    rows, preds = [], []
    for rep in range(rep0, rep0 + reps):
        for f, (tr, te) in enumerate(splits(df, scheme, rep)):
            mask = np.zeros(n, bool); mask[tr] = True
            NY = nb_mean(y[:, None], nbs, mask)[:, 0]
            seed = SEED + 100 * rep + f
            P = {}
            if "ridge" in models:
                P["ridge"] = RidgeCV(alphas=np.logspace(-3, 3, 13)).fit(Xs[tr], y[tr]).predict(Xs[te])
            if "lgbm" in models:
                P["lgbm"] = fit_lgbm(Xs, y, tr, te, seed)
            if "lgbm_nx" in models:
                P["lgbm_nx"] = fit_lgbm(np.c_[Xs, NX], y, tr, te, seed)
            if "lgbm_ny" in models:
                P["lgbm_ny"] = fit_lgbm(np.c_[Xs, NX, NY], y, tr, te, seed)
            for k in ("mlp", "gcn", "sage"):
                if k in models:
                    P[k] = fit_net(Xs, y, tr, te, A_s if k == "sage" else A_g, k, seed, layers)
            for k, p in P.items():
                e = y[te] - p
                rows.append({"tag": tag, "target": target, "graph": graph, "scheme": scheme, "layers": layers,
                             "rep": rep, "fold": f, "model": k, "n_test": len(te), "sse": float((e ** 2).sum()),
                             "sst": float(((y[te] - y[tr].mean()) ** 2).sum())})
                preds.append(pd.DataFrame({"tag": tag, "scheme": scheme, "rep": rep, "model": k,
                                           "code": df["code"].values[te], "y": y[te], "pred": p}))
    return pd.DataFrame(rows), pd.concat(preds)


def summarize(r):
    g = r.groupby(["tag", "target", "graph", "scheme", "layers", "model", "rep"]).agg(sse=("sse", "sum"), sst=("sst", "sum"), n=("n_test", "sum")).reset_index()
    g["rmse"] = np.sqrt(g.sse / g.n); g["r2"] = 1 - g.sse / g.sst
    s = g.groupby(["tag", "target", "graph", "scheme", "layers", "model"]).agg(rmse=("rmse", "mean"), rmse_sd=("rmse", "std"), r2=("r2", "mean"), r2_sd=("r2", "std"), reps=("rep", "nunique")).reset_index()
    return s


def stage(name, fn):
    """段階ごとに結果を保存し、保存済みならそれを読む（途中で止まっても続きから計算できるように）"""
    f = RES / "stages" / f"{name}.csv"
    fp = RES / "stages" / f"{name}_pred.csv"
    if f.exists():
        return pd.read_csv(f), (pd.read_csv(fp, dtype={"code": str}) if fp.exists() else None)
    f.parent.mkdir(exist_ok=True)
    r, p = fn()
    r.to_csv(f, index=False)
    if p is not None:
        p.to_csv(fp, index=False)
    print(name, flush=True)
    return r, p


if __name__ == "__main__":
    ALL = ["ridge", "lgbm", "lgbm_nx", "lgbm_ny", "mlp", "gcn", "sage"]
    REPS = 1 if QUICK else 3
    R2 = 1 if QUICK else 2  # 頑健性のほうは2回くり返し
    df, xs = load("tfr")
    res, pr = [], []
    # 1) 本体：全国、隣接グラフ、ランダムと空間ブロック（くり返しごとに保存）
    for scheme in ("random", "block"):
        for rep in range(REPS):
            r, p = stage(f"main_{scheme}_{rep}", lambda scheme=scheme, rep=rep: run(df, xs, "tfr", "adjacent", scheme, 1, ALL, tag="main", rep0=rep))
            res.append(r); pr.append(p)
    # 2) グラフの作り方：近い6区域
    for scheme in ("random", "block"):
        r, _ = stage(f"knn6_{scheme}", lambda scheme=scheme: (run(df, xs, "tfr", "knn6", scheme, R2, ["lgbm_nx", "lgbm_ny", "gcn", "sage"], tag="graph_knn6")[0], None)); res.append(r)
    # 3) 層の数：1・3層
    for L in (1, 3):
        for scheme in ("random", "block"):
            r, _ = stage(f"layers{L}_{scheme}", lambda L=L, scheme=scheme: (run(df, xs, "tfr", "adjacent", scheme, R2, ["gcn", "sage"], layers=L, tag=f"layers{L}")[0], None)); res.append(r)
    # 4) 対象を変える：高齢者の割合（指標から外して予測）
    df2, xs2 = load("aged")
    for scheme in ("random", "block"):
        r, _ = stage(f"aged_{scheme}", lambda scheme=scheme: (run(df2, xs2, "aged", "adjacent", scheme, R2, ALL, tag="target_aged")[0], None)); res.append(r)
    # 5) 1都3県だけ：隣接・近い6区域・通勤のグラフを比べる。分け方は、市区町村のランダム5分割と、都県ごとに1つずつ外す4分割
    sub = df[df.pref.isin(["11", "12", "13", "14"])].reset_index(drop=True)
    old = {c: i for i, c in enumerate(df.code)}
    keep = np.array([old[c] for c in sub.code])
    remap = {o: k for k, o in enumerate(keep)}
    _orig_edges = edges

    def edges_sub(kind, d):
        a, b = _orig_edges(kind, df)
        m = np.isin(a, keep) & np.isin(b, keep)
        return np.array([remap[x] for x in a[m]]), np.array([remap[x] for x in b[m]])

    edges = edges_sub  # noqa: F811
    for graph in ("adjacent", "knn6", "commute_top6", "commute_1pct"):
        for scheme in ("random", "block"):
            r, _ = stage(f"kanto_{graph}_{scheme}", lambda graph=graph, scheme=scheme: (run(sub, xs, "tfr", graph, scheme, REPS + 1, ["lgbm", "lgbm_nx", "lgbm_ny", "mlp", "gcn", "sage"], tag="kanto")[0], None)); res.append(r)
    edges = _orig_edges

    R = pd.concat(res)
    R.to_csv(RES / "folds.csv", index=False)
    pd.concat(pr).to_csv(RES / "predictions_main.csv", index=False)
    S = summarize(R)
    S.to_csv(RES / "summary.csv", index=False)
    print(S.round(4).to_string())
    json.dump({"n_nodes": len(df), "n_kanto": len(sub), "reps_main": REPS, "reps_robust": R2, "reps_kanto": REPS + 1}, open(RES / "run_info.json", "w"))
