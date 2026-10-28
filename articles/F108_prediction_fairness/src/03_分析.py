"""地価：F03 と同じ LightGBM を空間ブロックCVで当て直し、グループ別の外れ方（誤差・偏り・較正・区間のカバー率）を比べ、
4つの補正（グループ別の偏りの差し引き・重み付け・グループを特徴量に・グループ別の区間）を試す。頑健性もここで。"""
import json, numpy as np, pandas as pd
import lightgbm as lgb
from sklearn.model_selection import KFold, GroupKFold
from sklearn.linear_model import Ridge
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from common import RAW, RES, SEED, NUM, CAT, PARAMS, BLOCKS, KENS, DENS, USES

d = pd.read_csv(RAW / "land_groups.csv", dtype={"code": str, "muni": str, "pref": str})
for c in CAT: d[c] = d[c].astype("category")
d["y"] = np.log(d["price"])
FEAT = NUM + CAT
GROUPS = {"ken": KENS, "blk": BLOCKS, "dens": DENS, "use": USES}
GNAME = {"ken": "圏域", "blk": "地方ブロック", "dens": "人口密度", "use": "用途"}


def splits(df, kind, k=5):   # F03 の cvlib.splits と同じ
    if kind == "random":
        return list(KFold(k, shuffle=True, random_state=SEED).split(df))
    g = df["pref"] if kind == "pref" else df["block20"]
    rng = np.random.default_rng(SEED); u = g.unique(); perm = dict(zip(u, rng.permutation(len(u))))
    return list(GroupKFold(k).split(df, groups=g.map(perm)))


def foldid(df, kind):
    f = np.zeros(len(df), int)
    for i, (_, te) in enumerate(splits(df, kind)): f[te] = i
    return f


def oof_lgb(df, kind, feats=FEAT, weight=None, y="y"):
    p = np.full(len(df), np.nan)
    for tr, te in splits(df, kind):
        m = lgb.LGBMRegressor(**PARAMS)
        m.fit(df[feats].iloc[tr], df[y].iloc[tr], sample_weight=None if weight is None else weight[tr])
        p[te] = m.predict(df[feats].iloc[te])
    return p


def oof_ridge(df, kind):
    pre = ColumnTransformer([("n", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUM), ("c", make_pipeline(SimpleImputer(strategy="most_frequent"), OneHotEncoder(handle_unknown="ignore")), CAT)])
    p = np.full(len(df), np.nan)
    for tr, te in splits(df, kind):
        m = make_pipeline(pre, Ridge(alpha=1.0)).fit(df[FEAT].iloc[tr], df["y"].iloc[tr])
        p[te] = m.predict(df[FEAT].iloc[te])
    return p


CACHE = RES / "cache"; CACHE.mkdir(exist_ok=True)   # 途中結果（GitHub には置かない）


def cached(name, fn):
    f = CACHE / f"{name}.npy"
    if f.exists(): return np.load(f)
    v = fn(); np.save(f, v); return v


# F03 と同じ設定・同じ分け方なので、基本のモデルの予測は F03 の results/oof_lgbm.csv と一致する（確認済み）。
# あればそれを使い、なければ当て直す
F03OOF = RAW / "F03_oof_lgbm.csv"
def base_oof(kind):
    if F03OOF.exists():
        o = pd.read_csv(F03OOF, dtype={"code": str}).set_index("code")
        return o.loc[d["code"], f"lgb_{kind}"].values
    return cached(f"base_{kind}", lambda: oof_lgb(d, kind))


def interval_q(r, fold, g=None, level=0.9):
    """分割コンフォーマル（交差版）：各分割の区間の幅を、ほかの分割の |外れ| の分位点で決める。g を渡すとグループ別（Mondrian）"""
    a = np.abs(r); q = np.zeros(len(r))
    for f in np.unique(fold):
        te, tr = fold == f, fold != f
        if g is None:
            q[te] = np.quantile(a[tr], level)
        else:
            for gv in np.unique(g[te]):
                m = tr & (g == gv)
                q[te & (g == gv)] = np.quantile(a[m], level) if m.sum() >= 30 else np.quantile(a[tr], level)
    return q


def metrics(y, p, q=None, qm=None):
    r = p - y; ape = np.abs(np.exp(r) - 1)
    out = dict(n=len(y), med_ape=np.median(ape), bias=np.exp(np.mean(r)) - 1, within20=(ape <= 0.2).mean(),
               slope=np.polyfit(p, y, 1)[0] if len(y) > 2 else np.nan)
    if q is not None: out.update(cover=(np.abs(r) <= q).mean(), width=np.exp(2 * np.median(q)) - 1)
    if qm is not None: out.update(cover_m=(np.abs(r) <= qm).mean(), width_m=np.exp(2 * np.median(qm)) - 1)
    return out


def by_group(df, p, fold, gcol, label, level=0.9):
    y = df["y"].values; r = p - y; g = df[gcol].values
    q = interval_q(r, fold, None, level); qm = interval_q(r, fold, g, level)
    rows = [dict(setting=label, group_def=gcol, group="全体", **metrics(y, p, q, qm))]
    for gv in GROUPS[gcol]:
        m = g == gv
        if m.sum() >= 30: rows.append(dict(setting=label, group_def=gcol, group=gv, **metrics(y[m], p[m], q[m], qm[m])))
    return rows


def gap(rows, key):
    t = pd.DataFrame(rows); t = t[t.group != "全体"]
    return t[key].max() - t[key].min()


def bias_shift(df, p, fold, gcol):
    """グループ別の偏りを、ほかの分割の外れの平均で差し引く（交差版）"""
    r = p - df["y"].values; g = df[gcol].values; adj = p.copy()
    for f in np.unique(fold):
        te, tr = fold == f, fold != f
        for gv in np.unique(g[te]):
            adj[te & (g == gv)] -= r[tr & (g == gv)].mean()
    return adj


if __name__ == "__main__":
    fb = foldid(d, "block20")
    preds = {}
    print("基本（空間ブロックCV）"); preds["base_block20"] = base_oof("block20")
    allrows = []
    for gcol in GROUPS: allrows += by_group(d, preds["base_block20"], fb, gcol, "基本（空間ブロックCV）")
    # 価格帯：実際の価格で分けるか、予測した価格で分けるか
    y = d["y"].values; p = preds["base_block20"]; pr = []
    for basis, v in (("実際の価格", y), ("予測した価格", p)):
        qb = pd.qcut(pd.Series(v).rank(method="first"), 5, labels=[f"価格帯{i}" for i in range(1, 6)]).astype(str).values
        for gv in sorted(np.unique(qb)):
            m = qb == gv; pr.append(dict(basis=basis, group=gv, **metrics(y[m], p[m])))
    pd.DataFrame(pr).to_csv(RES / "price_band_bias.csv", index=False)

    # 補正
    corr = []
    for gcol in ("ken", "blk", "dens"):
        adj = bias_shift(d, p, fb, gcol); preds[f"shift_{gcol}"] = adj
        for g2 in GROUPS: corr += by_group(d, adj, fb, g2, f"偏りの差し引き（{GNAME[gcol]}別）")
    w = d["blk"].map(1 / d["blk"].value_counts()).values; w = w / w.mean()
    print("重み付け"); preds["reweight_blk"] = cached("reweight_blk", lambda: oof_lgb(d, "block20", weight=w))
    for g2 in GROUPS: corr += by_group(d, preds["reweight_blk"], fb, g2, "重み付け（ブロックごとの重みをそろえる）")
    for c in ("ken", "blk", "dens"): d[c + "_c"] = d[c].astype("category")
    print("グループを特徴量に"); preds["feat_groups"] = cached("feat_groups", lambda: oof_lgb(d, "block20", feats=FEAT + ["ken_c", "blk_c", "dens_c"]))
    for g2 in GROUPS: corr += by_group(d, preds["feat_groups"], fb, g2, "グループを特徴量に足す")
    pd.DataFrame(allrows + corr).to_csv(RES / "group_metrics_main.csv", index=False)

    # 頑健性
    rob = []
    for kind in ("random", "pref"):
        print(kind); preds[f"base_{kind}"] = base_oof(kind); f = foldid(d, kind)
        for g2 in GROUPS: rob += by_group(d, preds[f"base_{kind}"], f, g2, {"random": "ランダムCV", "pref": "都道府県ブロックCV"}[kind])
    print("リッジ"); preds["ridge_block20"] = cached("ridge_block20", lambda: oof_ridge(d, "block20"))
    for g2 in GROUPS: rob += by_group(d, preds["ridge_block20"], fb, g2, "線形（リッジ回帰）")
    for lev in (0.8, 0.95):
        for g2 in GROUPS: rob += by_group(d, p, fb, g2, f"区間の水準 {int(lev*100)}%", level=lev)
    d16 = d[d["price_2016"] > 0].reset_index(drop=True).copy(); d16["y"] = np.log(d16["price_2016"])
    print("2016"); p16 = cached("y2016_block20", lambda: oof_lgb(d16, "block20")); f16 = foldid(d16, "block20")
    for g2 in GROUPS: rob += by_group(d16, p16, f16, g2, "2016年の価格")
    pd.DataFrame(rob).to_csv(RES / "group_metrics_robust.csv", index=False)

    # 差の区間（20km四方のマスごとに取り直すクラスター・ブートストラップ、500回）
    rng = np.random.default_rng(SEED); cells = d["block20"].values; uc = np.unique(cells)
    idx_by = pd.Series(np.arange(len(d))).groupby(cells).apply(np.array).to_dict()
    def stat(ix, pp, gcol, a, b, key):
        yy, ppp, gg = y[ix], pp[ix], d[gcol].values[ix]
        ma, mb = gg == a, gg == b
        if key == "med_ape":
            f = lambda m: np.median(np.abs(np.exp(ppp[m] - yy[m]) - 1))
        else:
            f = lambda m: np.exp(np.mean(ppp[m] - yy[m])) - 1
        return f(ma) - f(mb)
    comps = [("ken", "地方圏", "東京圏"), ("dens", "密度1（低い）", "密度5（高い）"), ("use", "商業地", "住宅地"),
             ("blk", "四国", "関東")]
    boot = []
    for name, pp in (("基本", p), ("偏りの差し引き（ブロック別）", preds["shift_blk"])):
        for gcol, a, b in comps:
            for key in ("med_ape", "bias"):
                est = stat(np.arange(len(d)), pp, gcol, a, b, key); bs = []
                for _ in range(500):
                    ix = np.concatenate([idx_by[c] for c in rng.choice(uc, len(uc))]); bs.append(stat(ix, pp, gcol, a, b, key))
                boot.append(dict(setting=name, group_def=gcol, a=a, b=b, metric=key, est=est,
                                 lo=np.quantile(bs, 0.025), hi=np.quantile(bs, 0.975)))
    pd.DataFrame(boot).to_csv(RES / "gap_bootstrap.csv", index=False)
    out = pd.DataFrame({"code": d["code"], "y": y, "fold_block20": fb, **{k: v for k, v in preds.items()}})
    out.to_csv(RES / "oof_predictions.csv.gz", index=False, compression="gzip")
    print("done")
