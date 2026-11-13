"""650 散らばりが条件で変わるデータで、90%点を回帰で出すと、ふつうの回帰と分位点回帰はどれだけ違うのか

架空のデータ（500件）：x は 0〜10 の一様、y = 2 + 0.5x + s(x)·ε。3通り：
  H0 散らばり一定（s=1.3、ε は正規）／H1 散らばりが x で増える（s = 0.3 + 0.2x、ε は正規）／H2 H1 で ε が右に長い（中心をそろえた対数正規）
90%点を
  OLS ふつうの回帰の予測 + 1.2816 × 残差の標準偏差（散らばり一定・正規を仮定）
  QR 分位点回帰（τ=0.9、statsmodels QuantReg）
で出し、新しいデータ（2万件）で「90%点より下に入った割合」を x の区間ごと（0〜2・4〜6・8〜10）に数える。本当の90%点との差も測る。各300回。
数字は置いた散らばりの形で決まる。
"""
import json
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN, INK

SRC = "出典：架空のデータ（作成者が乱数で作成、seed 650）"
rng = np.random.default_rng(650)
N, NT, REPS = 500, 20000, 300
LN_S = 0.8
Z90 = stats.norm.ppf(0.9)
ln_mean, ln_sd = np.exp(LN_S ** 2 / 2), np.sqrt((np.exp(LN_S ** 2) - 1) * np.exp(LN_S ** 2))
LN_Q90 = (np.exp(LN_S * Z90) - ln_mean) / ln_sd


def scale(x, sc):
    return np.full_like(x, 1.3) if sc == "H0" else 0.3 + 0.2 * x


def eps(n, sc):
    if sc == "H2":
        return (np.exp(rng.normal(0, LN_S, n)) - ln_mean) / ln_sd
    return rng.normal(0, 1, n)


def draw(n, sc):
    x = rng.uniform(0, 10, n)
    return x, 2 + 0.5 * x + scale(x, sc) * eps(n, sc)


def true_q90(x, sc):
    return 2 + 0.5 * x + scale(x, sc) * (LN_Q90 if sc == "H2" else Z90)


BINS = [(0, 2), (4, 6), (8, 10)]
rows = []
for sc in ["H0", "H1", "H2"]:
    xt, yt = draw(NT, sc); qt = true_q90(xt, sc)
    Xt = sm.add_constant(xt)
    for r in range(REPS):
        x, y = draw(N, sc); X = sm.add_constant(x)
        ols = sm.OLS(y, X).fit()
        q_ols = Xt @ ols.params + Z90 * np.sqrt(ols.scale)
        qr = sm.QuantReg(y, X).fit(q=0.9)
        q_qr = Xt @ qr.params
        rec = {"scenario": sc, "rep": r}
        for name, q in [("ols", q_ols), ("qr", q_qr)]:
            below = yt <= q
            rec[f"{name}_all"] = below.mean() * 100
            for lo, hi in BINS:
                m = (xt >= lo) & (xt < hi)
                rec[f"{name}_{lo}_{hi}"] = below[m].mean() * 100
            rec[f"{name}_abs_err"] = np.abs(q - qt).mean()
        rows.append(rec)
D = pd.DataFrame(rows); D.to_csv(RES / "reps.csv.gz", index=False, float_format="%.5g", compression={"method": "gzip", "mtime": 0})
S = D.drop(columns="rep").groupby("scenario").mean().round(2)
S.to_csv(RES / "summary.csv")
out = {"n": N, "test_n": NT, "reps": REPS, "summary": S.to_dict(orient="index"),
       "lognormal_sigma": LN_S, "lognormal_std_q90": round(float(LN_Q90), 4), "normal_q90": round(float(Z90), 4)}
json.dump(out, open(RES / "a650_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：例（H2）の散布図と3本の線
x, y = draw(N, "H2"); X = sm.add_constant(x)
ols = sm.OLS(y, X).fit(); qr = sm.QuantReg(y, X).fit(q=0.9)
xx = np.linspace(0, 10, 100); XX = sm.add_constant(xx)
fig, ax = plt.subplots(figsize=(8.5, 4.3))
ax.scatter(x, y, s=6, color=GRAY, alpha=0.5)
ax.plot(xx, true_q90(xx, "H2"), color=INK, ls="--", lw=1.2, label="本当の90%点")
ax.plot(xx, XX @ ols.params + Z90 * np.sqrt(ols.scale), color=ORANGE, lw=2, label="ふつうの回帰＋1.28×標準偏差")
ax.plot(xx, XX @ qr.params, color=BLUE, lw=2, label="分位点回帰（90%）")
ax.set_xlabel("x"); ax.set_ylabel("y"); ax.legend(frameon=False, fontsize=9)
ax.set_title("散らばりが x で増え、右に長い例：ふつうの回帰の線は平行にずらしただけ")
save(fig, "a650_example.png", SRC)

# 図2：x の区間ごとの「下に入った割合」
fig, ax = plt.subplots(1, 3, figsize=(12, 3.9), sharey=True, gridspec_kw={"wspace": 0.1})
names = {"H0": "散らばり一定・正規", "H1": "x で増える・正規", "H2": "x で増える・右に長い"}
xl = ["x 0〜2", "x 4〜6", "x 8〜10"]
for a_, sc in zip(ax, ["H0", "H1", "H2"]):
    v1 = [S.loc[sc, f"ols_{lo}_{hi}"] for lo, hi in BINS]; v2 = [S.loc[sc, f"qr_{lo}_{hi}"] for lo, hi in BINS]
    xi = np.arange(3); w = 0.38
    a_.bar(xi - w / 2, v1, w, color=ORANGE, label="ふつうの回帰"); a_.bar(xi + w / 2, v2, w, color=BLUE, label="分位点回帰")
    for i in range(3):
        a_.text(i - w / 2, v1[i], f"{v1[i]:.0f}", ha="center", va="bottom", fontsize=8); a_.text(i + w / 2, v2[i], f"{v2[i]:.0f}", ha="center", va="bottom", fontsize=8)
    a_.axhline(90, color=INK, ls="--", lw=0.8); a_.set_xticks(xi); a_.set_xticklabels(xl); a_.set_title(names[sc], fontsize=11); a_.set_ylim(50, 105)
ax[0].set_ylabel("90%点より下に入った割合（%）"); ax[0].legend(frameon=False, fontsize=8.5, loc="lower left")
save(fig, "a650_by_bin.png", SRC, y=-0.06)

# 図3：全体の割合と本当の90%点との差
fig, ax = plt.subplots(1, 2, figsize=(11, 3.8), gridspec_kw={"wspace": 0.3})
xi = np.arange(3); w = 0.38; scs = ["H0", "H1", "H2"]
for i, (nm, c) in enumerate([("ols", ORANGE), ("qr", BLUE)]):
    ax[0].bar(xi + (i - 0.5) * w, [S.loc[s, f"{nm}_all"] for s in scs], w, color=c, label="ふつうの回帰" if nm == "ols" else "分位点回帰")
    ax[1].bar(xi + (i - 0.5) * w, [S.loc[s, f"{nm}_abs_err"] for s in scs], w, color=c)
ax[0].axhline(90, color=INK, ls="--", lw=0.8); ax[0].set_ylim(80, 95); ax[0].set_xticks(xi); ax[0].set_xticklabels([names[s] for s in scs], fontsize=8.5)
ax[0].set_title("全体で下に入った割合（%）", fontsize=11); ax[0].legend(frameon=False, fontsize=8.5)
ax[1].set_xticks(xi); ax[1].set_xticklabels([names[s] for s in scs], fontsize=8.5); ax[1].set_title("本当の90%点との差の平均", fontsize=11)
save(fig, "a650_overall.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1))
