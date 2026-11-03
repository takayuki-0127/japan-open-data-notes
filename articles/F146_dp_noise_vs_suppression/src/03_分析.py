"""03 分析：市区町村の集計表にラプラス機構でノイズを入れ、4種類の分析の答えがどれだけ変わるかを ε ごとに調べる。
あわせて、いまの「小さい値を伏せる（秘匿）」と比べる。個票は作らず、元の個人も推定しない（公表済みの集計表だけを使う）。

  A. 検診受診率（大腸がん、2023年度、1,656市区町村）：率の誤差、順位、上位50、ファンネルの外れ、規模との関係、県・全国の率
  B. 死亡（2018〜22年）：SMR の誤差と順位（全死因・脳血管疾患）
  C. 出生率の回帰（F20 の OLS）：総人口と15〜39歳女性の数にノイズ → 係数と決定係数
  D. 頑健性：ノイズの種類（離散）、後処理（0未満の切り上げ）、予算の分け方、年度・指標、集計の細かさ（県単位）
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
from common import DATA, RES, SEED, EPS, NREP, laplace, geometric

rng = np.random.default_rng(SEED)
out = {}

SIZE_BINS = [0, 500, 2000, 10000, np.inf]
SIZE_LAB = ["500人未満", "500〜2,000人", "2,000〜1万人", "1万人以上"]


def post(n_, y_, clamp=True):
    """後処理：人数を整数にし、0 未満を 0 に、受診者が対象者を超えないようにする"""
    n_ = np.round(n_)
    y_ = np.round(y_)
    if clamp:
        n_ = np.maximum(n_, 1)
        y_ = np.clip(y_, 0, n_)
    return n_, y_


def funnel_flag(n, y, p0, z=3.09):
    """ファンネルプロット（99.8%）の線の外か（二項分布の正規近似）"""
    se = np.sqrt(p0 * (1 - p0) / np.maximum(n, 1))
    r = y / np.maximum(n, 1)
    return np.where(r > p0 + z * se, 1, np.where(r < p0 - z * se, -1, 0))


def kappa(a, b):
    """3分類（上に外れ・内・下に外れ）の一致の κ"""
    cats = [-1, 0, 1]
    po = np.mean(a == b)
    pe = sum(np.mean(a == c) * np.mean(b == c) for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else np.nan


def topk(x, k=50):
    return set(np.argsort(-x)[:k])


def screening_metrics(n, y, nn, yy, pref, size_cls, true_top, true_flag, p_true, small_mask):
    r = y / n
    rr = yy / nn
    err = np.abs(rr - r) * 100
    m = {"mae_all": float(np.median(err))}
    for i, lab in enumerate(SIZE_LAB):
        m[f"mae_{lab}"] = float(np.median(err[size_cls == i]))
    m["spearman"] = float(stats.spearmanr(r, rr)[0])
    tk = topk(rr)
    m["top50_overlap"] = len(tk & true_top) / 50
    m["top50_small_share"] = float(np.mean(small_mask[list(tk)]))
    p_noisy = yy.sum() / nn.sum()
    m["national_err_pt"] = float(abs(p_noisy - p_true) * 100)
    m["funnel_kappa"] = float(kappa(true_flag, funnel_flag(nn, yy, p_noisy)))
    m["funnel_out_share"] = float(np.mean(funnel_flag(nn, yy, p_noisy) != 0))
    m["size_corr"] = float(stats.spearmanr(np.log(n), rr)[0])   # 分母は真の規模で区分（規模の区分自体は公表とみなす）
    # 県の率：市区町村のノイズ入りの数を足し上げたもの
    df = pd.DataFrame({"pref": pref, "n": n, "y": y, "nn": nn, "yy": yy}).groupby("pref").sum()
    m["pref_sum_err_pt"] = float(np.median(np.abs(df.yy / df.nn - df.y / df.n)) * 100)
    return m


# ---------------- A. 検診受診率 ----------------
scr_all = pd.read_csv(DATA / "screening.csv", dtype={"code": str})


def run_screening(year=2023, col="colon", mech="laplace", clamp=True, split=0.5, n_public=False, eps_list=EPS, nrep=NREP):
    d = scr_all[scr_all.year == year]
    n = d[f"n_{col}"].to_numpy(float)
    y = d[f"y_{col}"].to_numpy(float)
    pref = d.pref.to_numpy()
    size_cls = np.digitize(n, SIZE_BINS[1:-1])
    small = size_cls == 0
    r = y / n
    p_true = y.sum() / n.sum()
    true_top = topk(r)
    true_flag = funnel_flag(n, y, p_true)
    noise = laplace if mech == "laplace" else geometric
    rows = []
    for eps in eps_list:
        # 1人は「対象者」に1、「受診者」に最大1だけ効く → 2つの数を合わせた感度は2。
        # 予算を split : 1-split に分ける（ε_y = split·ε、ε_n = (1-split)·ε、どちらも感度1）
        if n_public:
            sc_y, sc_n = 1 / eps, None
        else:
            sc_y, sc_n = 1 / (split * eps), 1 / ((1 - split) * eps)
        for rep in range(nrep):
            yy = y + noise(rng, sc_y, len(y))
            nn = n if sc_n is None else n + noise(rng, sc_n, len(n))
            nn, yy = post(nn, yy, clamp)
            if not clamp:  # 切り上げなし：率は計算できる範囲（nn>0）だけ。負の率もそのまま
                nn = np.where(nn <= 0, np.nan, nn)
                ok = ~np.isnan(nn)
                rr = yy / nn
                rows.append({"eps": eps, "rep": rep,
                             "mae_500人未満": float(np.nanmedian(np.abs(rr - r)[small & ok]) * 100),
                             "bias_500人未満": float(np.nanmean((rr - r)[small & ok]) * 100),
                             "mae_all": float(np.nanmedian(np.abs(rr - r)) * 100)})
                continue
            m = screening_metrics(n, y, nn, yy, pref, size_cls, true_top, true_flag, p_true, small)
            m["bias_500人未満"] = float(np.mean((yy / nn - r)[small]) * 100)
            m.update(eps=eps, rep=rep)
            rows.append(m)
    res = pd.DataFrame(rows)
    base = {"n_units": int(len(n)), "national_rate": float(p_true * 100),
            "top50_small_share_true": float(np.mean(small[list(true_top)])),
            "funnel_out_share_true": float(np.mean(true_flag != 0)),
            "size_corr_true": float(stats.spearmanr(np.log(n), r)[0]),
            "small_share_all": float(small.mean()),
            "median_y_small": float(np.median(y[small])), "median_n_small": float(np.median(n[small]))}
    return res, base


scr, scr_base = run_screening()
scr.to_csv(RES / "screening_eps_reps.csv", index=False)
scr_med = scr.groupby("eps").median().drop(columns="rep")
scr_lo = scr.groupby("eps").quantile(0.025).drop(columns="rep")
scr_hi = scr.groupby("eps").quantile(0.975).drop(columns="rep")
scr_med.to_csv(RES / "screening_eps_median.csv")
scr_lo.to_csv(RES / "screening_eps_lo.csv")
scr_hi.to_csv(RES / "screening_eps_hi.csv")
out["screening_base"] = scr_base
out["screening_median"] = scr_med.round(4).reset_index().to_dict(orient="records")

# 県単位で直接ノイズを入れる場合（集計の細かさ）
d23 = scr_all[scr_all.year == 2023]
pt = d23.groupby("pref")[["n_colon", "y_colon"]].sum()
rows = []
for eps in EPS:
    for rep in range(NREP):
        nn = pt.n_colon.to_numpy() + laplace(rng, 2 / eps, len(pt))
        yy = pt.y_colon.to_numpy() + laplace(rng, 2 / eps, len(pt))
        nn, yy = post(nn, yy)
        rows.append({"eps": eps, "rep": rep, "pref_direct_err_pt": float(np.median(np.abs(yy / nn - pt.y_colon / pt.n_colon)) * 100)})
pdir = pd.DataFrame(rows).groupby("eps").median().drop(columns="rep")
out["pref_direct"] = pdir.round(5).reset_index().to_dict(orient="records")
pdir.to_csv(RES / "pref_direct.csv")

# いまのやり方：受診者が k 人未満の市区町村を伏せる（一次秘匿のみ）
d = d23
n = d.n_colon.to_numpy(float); y = d.y_colon.to_numpy(float); r = y / n
size_cls = np.digitize(n, SIZE_BINS[1:-1]); small = size_cls == 0
p_true = y.sum() / n.sum()
supp = []
for k in [10, 20, 50, 100]:
    keep = y >= k
    tk = set(np.where(keep)[0][np.argsort(-r[keep])[:50]])
    true_top = topk(r)
    dfp = pd.DataFrame({"pref": d.pref.to_numpy(), "n": n, "y": y, "keep": keep})
    g_all = dfp.groupby("pref")[["n", "y"]].sum()
    g_keep = dfp[dfp.keep].groupby("pref")[["n", "y"]].sum()
    pref_err = np.median(np.abs(g_keep.y / g_keep.n - g_all.y / g_all.n)) * 100
    supp.append({"k": k, "hidden_units": int((~keep).sum()), "hidden_share": float((~keep).mean()),
                 "hidden_small_share": float((~keep)[small].mean()),
                 "top50_overlap": len(tk & true_top) / 50,
                 "top50_small_share": float(np.mean(small[list(tk)])),
                 "size_corr": float(stats.spearmanr(np.log(n[keep]), r[keep])[0]),
                 "national_err_pt": float(abs(y[keep].sum() / n[keep].sum() - p_true) * 100),
                 "pref_err_pt": float(pref_err)})
supp = pd.DataFrame(supp)
supp.to_csv(RES / "suppression.csv", index=False)
out["suppression"] = supp.round(4).to_dict(orient="records")

# ---------------- B. 死亡（SMR） ----------------
dm = pd.read_csv(DATA / "deaths.csv", dtype={"code": str})
smr_rows = []
smr_base = {}
for cause in ["all", "stroke"]:
    dd = dm.dropna(subset=[f"O_{cause}", f"E_{cause}"])
    O = dd[f"O_{cause}"].to_numpy(float); E = dd[f"E_{cause}"].to_numpy(float)
    smr = O / E
    smr_base[cause] = {"n_units": int(len(O)), "median_O": float(np.median(O)), "share_O_lt30": float(np.mean(O < 30))}
    ttop = topk(smr)
    for eps in EPS:
        for rep in range(NREP):
            OO = np.maximum(np.round(O + laplace(rng, 1 / eps, len(O))), 0)  # 1人の死亡は1つの地域の1つの数にだけ入る → 感度1
            ss = OO / E
            smr_rows.append({"cause": cause, "eps": eps, "rep": rep,
                             "mae_smr": float(np.median(np.abs(ss - smr))),
                             "spearman": float(stats.spearmanr(smr, ss)[0]),
                             "top50_overlap": len(topk(ss) & ttop) / 50})
smr_res = pd.DataFrame(smr_rows)
smr_med = smr_res.groupby(["cause", "eps"]).median().drop(columns="rep")
smr_med.to_csv(RES / "smr_eps_median.csv")
out["smr_base"] = smr_base
out["smr_median"] = smr_med.round(4).reset_index().to_dict(orient="records")
out["smr_stroke_already_missing"] = int(dm.O_stroke.isna().sum())

# ---------------- C. 出生率の回帰（F20 の OLS） ----------------
f = pd.read_csv(DATA / "tfr_reg.csv", dtype={"code": str})
X = ["young_f", "income", "commute_out", "nursery", "tertiary", "density"]


def ols(df):
    Z = (df[X] - df[X].mean()) / df[X].std()
    A = np.c_[np.ones(len(df)), Z.to_numpy()]
    b, *_ = np.linalg.lstsq(A, df.tfr.to_numpy(), rcond=None)
    resid = df.tfr.to_numpy() - A @ b
    r2 = 1 - resid.var() / df.tfr.var(ddof=0)
    return dict(zip(X, b[1:])), r2


b_true, r2_true = ols(f)
# 真の係数の標準誤差（ノイズの影響を標本のぶれと比べるため）
Z = (f[X] - f[X].mean()) / f[X].std()
A = np.c_[np.ones(len(f)), Z.to_numpy()]
resid = f.tfr.to_numpy() - A @ np.linalg.lstsq(A, f.tfr.to_numpy(), rcond=None)[0]
s2 = resid @ resid / (len(f) - A.shape[1])
se_true = dict(zip(X, np.sqrt(np.diag(s2 * np.linalg.inv(A.T @ A)))[1:]))
reg_rows = []
for eps in EPS:
    for rep in range(NREP):
        g = f.copy()
        # 1人は「総人口」に1、「15〜39歳女性」に最大1 → 予算を半分ずつ（感度はそれぞれ1）
        pop = np.maximum(np.round(g["pop"] + laplace(rng, 2 / eps, len(g))), 1)
        nyf = np.clip(np.round(g["n_young_f"] + laplace(rng, 2 / eps, len(g))), 0, pop)
        g["young_f"] = 100 * nyf / pop
        g["density"] = np.log(pop / g["area"])
        b, r2 = ols(g)
        reg_rows.append({"eps": eps, "rep": rep, "r2": r2, **{f"b_{k}": v for k, v in b.items()}})
reg = pd.DataFrame(reg_rows)
reg_med = reg.groupby("eps").median().drop(columns="rep")
reg_lo = reg.groupby("eps").quantile(0.025).drop(columns="rep")
reg_hi = reg.groupby("eps").quantile(0.975).drop(columns="rep")
reg_med.to_csv(RES / "reg_eps_median.csv"); reg_lo.to_csv(RES / "reg_eps_lo.csv"); reg_hi.to_csv(RES / "reg_eps_hi.csv")
out["reg_true"] = {"coef": b_true, "se": se_true, "r2": r2_true, "n": int(len(f)),
                   "min_pop": float(f["pop"].min()), "median_pop": float(f["pop"].median()),
                   "min_young_f_count": float(f["n_young_f"].min())}
out["reg_median"] = reg_med.round(4).reset_index().to_dict(orient="records")
out["reg_lo"] = reg_lo.round(4).reset_index().to_dict(orient="records")
out["reg_hi"] = reg_hi.round(4).reset_index().to_dict(orient="records")

# ---------------- D. 頑健性 ----------------
rob = []
E2 = [0.1, 1.0]
def add(label, res):
    g = res.groupby("eps").median()
    for eps in E2:
        row = {"check": label, "eps": eps}
        for c in ["mae_all", "mae_500人未満", "spearman", "top50_overlap", "top50_small_share", "funnel_kappa", "bias_500人未満"]:
            if c in g.columns:
                row[c] = float(g.loc[eps, c])
        rob.append(row)

add("基本（ラプラス・切り上げあり・予算半々・2023年度・大腸）", scr[scr.eps.isin(E2)])
add("離散ラプラス（整数のノイズ）", run_screening(mech="geometric", eps_list=E2)[0])
add("後処理なし（0未満もそのまま）", run_screening(clamp=False, eps_list=E2)[0])
add("予算を受診者に3/4", run_screening(split=0.75, eps_list=E2)[0])
add("対象者数は公表とみなす（受診者だけにノイズ）", run_screening(n_public=True, eps_list=E2)[0])
for yr in [2021, 2022, 2024]:
    add(f"{yr}年度", run_screening(year=yr, eps_list=E2)[0])
add("肺がん検診", run_screening(col="lung", eps_list=E2)[0])
rob = pd.DataFrame(rob)
rob.to_csv(RES / "robustness.csv", index=False)
out["robustness"] = rob.round(4).to_dict(orient="records")

# ε ごとの期待される絶対誤差（ラプラス尺度 b の平均絶対値 = b）
out["expected_abs_noise_count"] = {str(e): 2 / e for e in EPS}

json.dump(out, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1, default=float)
print(json.dumps({k: out[k] for k in ["screening_base", "suppression", "reg_true", "smr_base"]}, ensure_ascii=False, indent=1, default=float))
print(scr_med[["mae_all", "mae_500人未満", "mae_1万人以上", "spearman", "top50_overlap", "top50_small_share", "funnel_kappa", "size_corr", "national_err_pt", "pref_sum_err_pt", "bias_500人未満"]].round(3))
print(pdir.round(4))
print(smr_med.round(3))
print(reg_med.round(3)); print(reg_lo.round(3)); print(reg_hi.round(3))
print(rob.round(3).to_string())
