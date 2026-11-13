"""617 時間で効き方の変わる要因に、Cox の比例ハザードモデルを当てると、ハザード比は何を表すのか

架空の会員4,000人（半分は入会時の割引で入った会員）。退会の起きやすさ（ハザード）は月4%が基本で、割引の会員は
入会0〜3か月は3.0倍、3〜12か月は1.0倍、12か月以降は0.7倍（本当のハザード比が時間で変わる）。
  C1 Cox モデル（割引のありなし1つ）で、ハザード比を1つ出す
  C2 期間を分けて（0〜3・3〜12・12か月〜）期間ごとのハザード比を出す
  C3 Schoenfeld 残差による比例ハザードの検定
観察の長さ（6・12・24・36か月で打ち切り）を変えると、1つのハザード比がどう変わるかも見る（各200回）。seed 617。
"""
import json
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.statistics import proportional_hazard_test
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

warnings.filterwarnings("ignore")
SRC = "出典：シミュレーション（作成者が乱数で作成、seed 617）"
rng = np.random.default_rng(617)
H0 = 0.04
CUTS = [0, 3, 12, np.inf]
HR = [3.0, 1.0, 0.7]
N = 4000


def draw(promo, rs):
    """区間ごとに一定のハザードの退会までの月数（逆関数法）"""
    e = rs.exponential(1.0, len(promo))
    t = np.zeros(len(promo))
    rem = e.copy(); done = np.zeros(len(promo), bool)
    for (a, b), m in zip(zip(CUTS[:-1], CUTS[1:]), HR):
        h = H0 * np.where(promo == 1, m, 1.0)
        width = b - a
        need = rem / h
        fin = (~done) & (need <= width)
        t[fin] = a + need[fin]
        rem = np.where(~done & ~fin, rem - h * width, rem)
        done |= fin
    return t


def make(follow, rs):
    promo = (rs.random(N) < 0.5).astype(int)
    t = draw(promo, rs)
    # 入会の時期がばらつく：観察の長さは follow か月まで一様に（遅く入会した人は短い）
    cens = rs.uniform(follow * 0.5, follow, N)
    T = np.minimum(t, cens); E = (t <= cens).astype(int)
    return pd.DataFrame({"T": T, "E": E, "promo": promo})


def split(df):
    rows = []
    for (a, b), lab in zip(zip(CUTS[:-1], CUTS[1:]), ["p0_3", "p3_12", "p12_"]):
        s = df[df["T"] > a].copy()
        s["start"] = a; s["stop"] = np.minimum(s["T"], b); s["event"] = ((s["T"] <= b) & (s.E == 1)).astype(int)
        s["period"] = lab
        rows.append(s)
    return pd.concat(rows)


main = make(36, rng)
main.round(4).to_csv(RES / "members_follow36.csv", index=False)
cph = CoxPHFitter().fit(main, "T", "E")
hr1 = float(np.exp(cph.params_["promo"])); ci1 = np.exp(cph.confidence_intervals_.loc["promo"].values)
pht = proportional_hazard_test(cph, main, time_transform="rank")
pval = float(pht.summary.loc["promo", "p"])
# 期間ごと：期間ごとに別の Cox（左打ち切りつき）で推定
from lifelines import CoxTimeVaryingFitter
sp = split(main); per = {}
for lab, s in sp.groupby("period"):
    s = s.assign(id=np.arange(len(s)))
    ctv = CoxTimeVaryingFitter().fit(s[["id", "start", "stop", "event", "promo"]], id_col="id", event_col="event", start_col="start", stop_col="stop")
    per[lab] = {"hr": round(float(np.exp(ctv.params_["promo"])), 3),
                "ci": [round(float(x), 3) for x in np.exp(ctv.confidence_intervals_.loc["promo"].values)], "events": int(s.event.sum())}
# 観察の長さを変える
fol = []
for follow in [6, 12, 24, 36]:
    hrs, ps = [], []
    for r in range(200):
        d = make(follow, np.random.default_rng(617_000 + 1000 * follow + r))
        c = CoxPHFitter().fit(d, "T", "E")
        hrs.append(float(np.exp(c.params_["promo"])))
        if r < 100:
            ps.append(float(proportional_hazard_test(c, d, time_transform="rank").summary.loc["promo", "p"]))
    fol.append({"follow_months": follow, "hr_median": round(float(np.median(hrs)), 3), "hr_p10": round(float(np.quantile(hrs, 0.1)), 3),
                "hr_p90": round(float(np.quantile(hrs, 0.9)), 3), "ph_test_reject_pct": round(100 * float(np.mean(np.array(ps) < 0.05)), 1)})
fol = pd.DataFrame(fol); fol.to_csv(RES / "by_follow.csv", index=False)
out = {"n": N, "base_hazard_per_month": H0, "true_hr_by_period": dict(zip(["0-3", "3-12", "12-"], HR)),
       "follow36": {"cox_hr": round(hr1, 3), "cox_ci": [round(float(x), 3) for x in ci1], "ph_test_p": pval,
                    "events": int(main.E.sum()), "by_period": per},
       "by_follow": fol.to_dict(orient="records")}
json.dump(out, open(RES / "a617_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：生存曲線（36か月）
fig, ax = plt.subplots(figsize=(8, 3.8))
for g, c, lab in [(0, BLUE, "ふつうの入会"), (1, ORANGE, "割引で入会")]:
    s = main[main.promo == g]
    km = KaplanMeierFitter().fit(s["T"], s["E"])
    ax.step(km.survival_function_.index, km.survival_function_.iloc[:, 0] * 100, where="post", color=c, label=lab)
ax.set_xlabel("入会からの月数"); ax.set_ylabel("在籍している割合（%）"); ax.legend(frameon=False)
ax.set_title("割引で入った会員は最初の3か月で多く辞め、そのあとは辞めにくい")
save(fig, "a617_survival.png", SRC)
# 図2：期間ごとのハザード比と、1つのハザード比
fig, ax = plt.subplots(figsize=(8, 3.8))
labs = ["0〜3か月", "3〜12か月", "12か月〜"]
for i, (k, lab) in enumerate(zip(["p0_3", "p3_12", "p12_"], labs)):
    v = per[k]
    ax.plot([i, i], v["ci"], color=GREEN, lw=2); ax.plot(i, v["hr"], "o", color=GREEN, ms=8)
    ax.plot(i, HR[i], "x", color=GRAY, ms=10, mew=2)
    ax.text(i + 0.08, v["hr"], f"{v['hr']:.2f}", va="center", fontsize=9)
ax.axhline(hr1, color=ORANGE, ls="--", label=f"Cox モデルの1つのハザード比 {hr1:.2f}")
ax.axhline(1, color=GRAY, lw=0.6)
ax.set_xticks(range(3)); ax.set_xticklabels(labs); ax.set_yscale("log"); ax.set_yticks([0.5, 0.7, 1, 2, 3, 4]); ax.set_yticks([], minor=True); ax.set_yticklabels(["0.5", "0.7", "1", "2", "3", "4"])
ax.set_xlim(-0.4, 2.5)
ax.set_ylabel("割引の会員のハザード比"); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("期間ごとのハザード比（緑、×は本当の値）と、まとめた1つの値")
save(fig, "a617_hr_by_period.png", SRC)
# 図3：観察の長さと1つのハザード比
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(fol.follow_months, fol.hr_median, marker="o", color=ORANGE, label="中央値（200回）")
ax.fill_between(fol.follow_months, fol.hr_p10, fol.hr_p90, color=ORANGE, alpha=0.2, label="10%〜90%")
ax.axhline(1, color=GRAY, lw=0.6)
for x, y in zip(fol.follow_months, fol.hr_median):
    ax.text(x + 0.6, y + 0.04, f"{y:.2f}", fontsize=9)
ax.set_xticks(fol.follow_months); ax.set_xlim(3, 39); ax.set_xlabel("観察の長さ（か月）。どの長さでも、比例ハザードの検定は100回中100回「崩れている」"); ax.set_ylabel("Cox モデルのハザード比")
ax.set_ylim(0.8, max(fol.hr_p90) + 0.5); ax.legend(frameon=False, fontsize=9, loc="upper right")
ax.set_title("同じ会員でも、いつまで観察したかで「1つのハザード比」が変わる")
save(fig, "a617_hr_by_follow.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
