"""621 A/B テストの割り付けが 50:50 からずれていることに、何人集まれば気づけるのか

予定は A:B = 50:50。B 側だけ、記録の取りこぼしで一部の人が消えるとする（消える割合 L）。
消えるのは、すぐ離れて申込みをしない人（申込み率 0）と置く。本当の効果は 0（A も B も申込み率 5%）。
  1) 割り付けの比の確認（SRM、カイ二乗の適合度検定、p<0.001）で、何人集まれば気づけるか（各 2,000 回）
  2) ずれたまま申込み率を比べると、効果 0 でも B が何%良く見え、何%の回で「差あり」（p<0.05）になるか
  3) 1日1万人・28日・B の 2% が消える例で、累計の比と p 値の動き。SQL（DuckDB、1スレッド）で人数とカイ二乗の値を出し、Python と一致を確かめる
数字は置いた消え方で決まる。
"""
import json
import numpy as np
import pandas as pd
import duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT, INK

SRC = "出典：架空の A/B テストの割り付け（作成者が乱数で作成、seed 621）"
rng = np.random.default_rng(621)
DATA.mkdir(exist_ok=True)
LOSS = [0.0, 0.005, 0.01, 0.02, 0.05]
NS = [1_000, 3_000, 10_000, 30_000, 100_000, 300_000, 1_000_000]
REPS, ALPHA_SRM, CR = 2000, 0.001, 0.05


def srm_p(na, nb):
    n = na + nb
    chi2 = (na - n / 2) ** 2 / (n / 2) + (nb - n / 2) ** 2 / (n / 2)
    return stats.chi2.sf(chi2, 1), chi2


# 1) 気づける割合
det = []
for L in LOSS:
    for n in NS:
        na = rng.binomial(n, 0.5, REPS)
        nb = rng.binomial(n - na, 1 - L)
        p, _ = srm_p(na, nb)
        det.append({"loss": L, "n_planned": n, "detect_pct": 100 * (p < ALPHA_SRM).mean(), "share_b_mean": float((nb / (na + nb)).mean())})
det = pd.DataFrame(det)
det.to_csv(RES / "srm_detection.csv", index=False)


def need_n(L, power=0.8):
    # 予定人数 n での期待のずれから、非心カイ二乗で 80% に届く人数を探す
    crit = stats.chi2.ppf(1 - ALPHA_SRM, 1)
    if L == 0:
        return None
    q = 0.5 * (1 - L) / (1 - 0.5 * L)  # 観測される B の割合
    for n in np.unique(np.logspace(2, 8, 2000).astype(int)):
        m = n * (1 - 0.5 * L)
        lam = m * (q - 0.5) ** 2 / 0.25
        if stats.ncx2.sf(crit, 1, lam) >= power:
            return int(n)


need = {str(L): need_n(L) for L in LOSS if L > 0}

# 2) ずれたまま比べた効果（予定 各群10万人、本当の効果0）
PER = 100_000
eff = []
for L in LOSS:
    lifts, fp = [], 0
    for r in range(REPS):
        na, nb_raw = PER, PER
        ya = rng.binomial(na, CR); yb_raw = rng.binomial(nb_raw, CR)
        lost = rng.binomial(nb_raw - yb_raw, L)  # 消えるのは申込みをしない人
        nb, yb = nb_raw - lost, yb_raw
        pa, pb = ya / na, yb / nb
        pp = (ya + yb) / (na + nb)
        z = (pb - pa) / np.sqrt(pp * (1 - pp) * (1 / na + 1 / nb))
        lifts.append(pb / pa - 1); fp += 2 * stats.norm.sf(abs(z)) < 0.05
    eff.append({"loss": L, "lift_pct_mean": 100 * float(np.mean(lifts)), "sig_pct": 100 * fp / REPS})
eff = pd.DataFrame(eff)
eff.to_csv(RES / "bias_under_srm.csv", index=False)

# 3) 例：1日1万人・28日、B の消える割合 1%
DAYS, PERDAY, LX = 28, 10_000, 0.02
ex = []
for d in range(1, DAYS + 1):
    arm = np.where(rng.random(PERDAY) < 0.5, "A", "B")
    conv = (rng.random(PERDAY) < CR).astype(int)
    keep = ~((arm == "B") & (conv == 0) & (rng.random(PERDAY) < LX))
    ex.append(pd.DataFrame({"day": d, "arm": arm[keep], "converted": conv[keep]}))
EX = pd.concat(ex, ignore_index=True)
EX.insert(0, "user_id", np.arange(1, len(EX) + 1))
EX.to_csv(DATA / "assignments.csv", index=False)
cum = EX.groupby(["day", "arm"]).size().unstack().cumsum()
cum["share_b"] = cum.B / (cum.A + cum.B)
cum["p"] = [srm_p(a, b)[0] for a, b in zip(cum.A, cum.B)]
cum.round(6).to_csv(RES / "example_cumulative.csv")
first_day = int(cum.index[cum.p < ALPHA_SRM][0]) if (cum.p < ALPHA_SRM).any() else None

con = duckdb.connect(); con.execute("SET threads=1"); con.register("assignments", EX)
q = (SQL / "02_srm_check_duckdb.sql").read_text(encoding="utf-8").split(";")[0]
na_s, nb_s, n_s, sh_s, chi_s = con.execute(q).fetchone()
p_py, chi_py = srm_p(int(cum.A.iloc[-1]), int(cum.B.iloc[-1]))
assert na_s == cum.A.iloc[-1] and nb_s == cum.B.iloc[-1] and abs(chi_s - chi_py) < 1e-9
pd.DataFrame([{"n_a": na_s, "n_b": nb_s, "share_b": sh_s, "chi2": chi_s, "p": p_py}]).to_csv(RES / "sql_example.csv", index=False)

out = {"alpha_srm": ALPHA_SRM, "reps": REPS, "conversion": CR, "detection": det.to_dict(orient="records"), "n_needed_80pct": need,
       "bias_per_arm_100k": eff.round(3).to_dict(orient="records"),
       "example": {"days": DAYS, "per_day": PERDAY, "loss": LX, "first_day_p_lt_0.001": first_day,
                   "final_share_b": round(float(cum.share_b.iloc[-1]), 5), "final_chi2": round(float(chi_py), 3), "final_p": float(p_py),
                   "n_a": int(na_s), "n_b": int(nb_s)}}
json.dump(out, open(RES / "a621_main.json", "w"), ensure_ascii=False, indent=1)
det.merge(eff, on="loss").to_csv(RES / "summary.csv", index=False)

# 図1
fig, ax = plt.subplots(figsize=(8.5, 4.2))
for L, c in zip(LOSS, [GRAY, LIGHT, BLUE, ORANGE, INK]):
    s = det[det.loss == L]
    ax.plot(s.n_planned, s.detect_pct, marker="o", color=c, label=f"B の {L*100:g}% が消える" if L else "ずれなし")
ax.set_xscale("log"); ax.set_xlabel("集まった人数（予定、対数目盛）"); ax.set_ylabel("ずれに気づく回の割合（%）")
ax.set_title("割り付けの比の確認（p<0.001）でずれに気づける割合"); ax.legend(frameon=False, fontsize=9)
save(fig, "a621_detection.png", SRC)

# 図2
fig, ax = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"wspace": 0.3})
lab = [f"{L*100:g}%" for L in LOSS]
ax[0].bar(lab, eff.lift_pct_mean, color=BLUE)
for i, v in enumerate(eff.lift_pct_mean):
    ax[0].text(i, v, f"{v:+.2f}%", ha="center", va="bottom", fontsize=9)
ax[0].set_title("B の申込み率の見かけの上乗せ（本当は 0）"); ax[0].set_xlabel("B から消える人の割合")
ax[1].bar(lab, eff.sig_pct, color=ORANGE)
for i, v in enumerate(eff.sig_pct):
    ax[1].text(i, v, f"{v:.1f}%", ha="center", va="bottom", fontsize=9)
ax[1].axhline(5, color=GRAY, ls=":"); ax[1].set_title("「差あり」（p<0.05）と出た回の割合"); ax[1].set_xlabel("B から消える人の割合")
save(fig, "a621_bias.png", SRC, y=-0.05)

# 図3
fig, ax = plt.subplots(1, 2, figsize=(11, 4), gridspec_kw={"wspace": 0.3})
ax[0].plot(cum.index, cum.share_b * 100, marker="o", ms=3, color=BLUE); ax[0].axhline(50, color=GRAY, ls=":")
ax[0].set_title("累計の B の割合（%）"); ax[0].set_xlabel("日数")
ax[1].plot(cum.index, cum.p, marker="o", ms=3, color=ORANGE); ax[1].set_yscale("log"); ax[1].axhline(ALPHA_SRM, color=INK, ls="--", lw=0.8)
ax[1].set_title("割り付けの比の確認の p 値（対数目盛、破線 0.001）"); ax[1].set_xlabel("日数")
save(fig, "a621_example_days.png", SRC, y=-0.05)
print(det.pivot(index="n_planned", columns="loss", values="detect_pct")); print(eff); print(need); print(out["example"])
