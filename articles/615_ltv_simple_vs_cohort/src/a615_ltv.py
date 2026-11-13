"""615 顧客の生涯の売上を「月の購入額÷退会率」で出すと、登録月ごとの実績からどれだけずれるのか

架空の会員制の店。2023年1月〜2025年12月に毎月1,000人が入会。会員は2種類：
  ライト（6割）：月の退会率12%、在籍中の月の購入額 平均2,000円
  ヘビー（4割）：月の退会率3%、月の購入額 平均5,000円
長く残るのはヘビーなので、在籍している会員の顔ぶれは、入会したばかりの会員と違う。
  L1 簡便式（在籍者全体）：2025年12月の在籍者の月の購入額÷その月の退会率
  L2 簡便式（入会12か月以内）：入会から12か月以内の会員で出した購入額÷退会率
  L3 登録月ごとの実績：入会した人1人あたりの累計の購入額を月ごとに足し、観測の終わりから先は直近6か月の減り方で延ばす
本当の値は、種類ごとの退会率と購入額から計算した、入会した人1人あたりの10年間の購入額（割り引きなし）。
DuckDB（1スレッド）の SQL と pandas で簡便式の材料が一致することを確かめる。seed 615。
"""
import json
import numpy as np
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
from common import RES, SQL, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：架空の会員（作成者が乱数で作成、seed 615）"
rng = np.random.default_rng(615)
TYPES = {"light": (0.6, 0.12, 2000.0), "heavy": (0.4, 0.03, 5000.0)}
months = pd.date_range("2023-01-01", "2025-12-01", freq="MS")
NJ = 1000
recs = []
mid = 0
for j, jm in enumerate(months):
    typ = rng.choice(["light", "heavy"], NJ, p=[0.6, 0.4])
    for t in typ:
        mid += 1
        _, h, sp = TYPES[t]
        for k in range(j, len(months)):
            churn = rng.random() < h
            spend = float(np.round(rng.gamma(2.0, sp / 2.0), -1))
            recs.append((mid, months[k], jm, t, True, churn, spend))
            if churn:
                break
MM = pd.DataFrame(recs, columns=["member_id", "ym", "joined_ym", "type", "active", "churned_this_month", "spend"])
con = duckdb.connect(); con.execute("SET threads=1"); con.register("member_month", MM)
q = [x for x in (SQL / "02_ltv_inputs_duckdb.sql").read_text(encoding="utf-8").split(";") if "SELECT" in x]
arpu, churn = con.execute(q[0]).fetchone()
arpu_new, churn_new = con.execute(q[1]).fetchone()
last = MM[MM.ym == months[-1]]
assert abs(arpu - last.spend.mean()) < 1e-6 and abs(churn - last.churned_this_month.mean()) < 1e-9
MM["age"] = (MM.ym.dt.year - MM.joined_ym.dt.year) * 12 + (MM.ym.dt.month - MM.joined_ym.dt.month)
nw = MM[MM.age < 12]
assert abs(arpu_new - nw.spend.mean()) < 1e-6 and abs(churn_new - nw.churned_this_month.mean()) < 1e-9
L1 = arpu / churn
L2 = arpu_new / churn_new
# L3：入会した人1人あたりの、入会からの月数ごとの購入額（観測できる登録月だけで平均）
joined = MM.groupby("joined_ym").member_id.nunique()
per_age = MM.groupby(["joined_ym", "age"]).spend.sum().unstack(fill_value=np.nan)
curve = []
for a in range(len(months)):
    ok = [jm for jm in joined.index if (len(months) - 1 - months.get_loc(jm)) >= a]
    curve.append(float(per_age.loc[ok, a].fillna(0).sum() / joined.loc[ok].sum()))
curve = np.array(curve)
obs = curve.sum()
r = (curve[-6:] / curve[-7:-1]).mean()          # 直近6か月の減り方（1か月あたりの比）
tail = curve[-1] * sum(r ** k for k in range(1, 120 - len(curve) + 1))
L3 = obs + tail
# 本当の値（10年＝120か月、割り引きなし、在籍した月に購入額を足す）
def true_ltv(H):
    return sum(w * sp * sum((1 - h) ** k for k in range(H)) for w, h, sp in TYPES.values())
T120, Tinf = true_ltv(120), sum(w * sp / h for w, h, sp in TYPES.values())
true_curve = np.array([sum(w * sp * (1 - h) ** k for w, h, sp in TYPES.values()) for k in range(120)])
# 観測の長さを変えたときの L3（12・24・36か月の実績＋延長）
L3_by_len = {}
for n in [12, 24, 36]:
    c = curve[:n]; rr = (c[-6:] / c[-7:-1]).mean()
    L3_by_len[n] = float(c.sum() + c[-1] * sum(rr ** k for k in range(1, 120 - n + 1)))
active_mix = last.type.value_counts(normalize=True).round(3).to_dict()
out = {"joins_per_month": NJ, "months": len(months), "member_months": int(len(MM)),
       "L1_simple_active_base": round(L1), "arpu_active": round(arpu), "churn_active_pct": round(100 * churn, 2), "active_mix_dec2025": active_mix,
       "L2_simple_first12m": round(L2), "arpu_new": round(arpu_new), "churn_new_pct": round(100 * churn_new, 2),
       "L3_cohort_extrapolated": round(L3), "L3_observed_36m_part": round(obs), "L3_by_observed_length": {k: round(v) for k, v in L3_by_len.items()},
       "true_10y": round(T120), "true_infinite": round(Tinf),
       "L1_vs_true_pct": round(100 * (L1 / T120 - 1), 1), "L2_vs_true_pct": round(100 * (L2 / T120 - 1), 1), "L3_vs_true_pct": round(100 * (L3 / T120 - 1), 1)}
json.dump(out, open(RES / "a615_main.json", "w"), ensure_ascii=False, indent=1)
pd.DataFrame({"age": np.arange(len(curve)), "observed_per_joined": curve.round(1), "true": true_curve[:len(curve)].round(1)}).to_csv(RES / "curve.csv", index=False)

# 図1：3つの見積もりと本当の値
fig, ax = plt.subplots(figsize=(8.5, 3.8))
lab = ["簡便式\n（在籍者全体）", "簡便式\n（入会12か月以内）", "登録月ごとの実績\n＋延長", "本当の値\n（10年）"]
v = [L1, L2, L3, T120]
ax.bar(lab, np.array(v) / 1e4, color=[ORANGE, BLUE, GREEN, GRAY])
for i, x in enumerate(v):
    ax.text(i, x / 1e4, f"{x / 1e4:.1f}万円" + (f"\n（{100 * (x / T120 - 1):+.0f}%）" if i < 3 else ""), ha="center", va="bottom", fontsize=9)
ax.set_ylabel("入会した人1人あたりの生涯の購入額（万円）"); ax.set_ylim(0, max(v) / 1e4 * 1.3)
ax.set_title("生涯の購入額の見積もり：簡便式は本当の値より小さく出た")
save(fig, "a615_ltv_estimates.png", SRC, y=-0.08)
# 図2：入会からの月ごとの、入会した人1人あたりの購入額
fig, ax = plt.subplots(figsize=(8.5, 3.8))
ax.plot(range(len(curve)), curve, marker="o", ms=3, color=GREEN, label="実績（入会した人1人あたり）")
k = np.arange(len(curve), 120)
ax.plot(k, curve[-1] * r ** (k - len(curve) + 1), color=GREEN, ls="--", label="直近6か月の減り方で延長")
ax.plot(range(120), true_curve, color=GRAY, lw=1, label="本当の値")
ax.set_xlabel("入会からの月数"); ax.set_ylabel("その月の購入額（円）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("入会からの月ごとの購入額：最初の1年で急に減り、そのあとはゆっくり")
save(fig, "a615_cohort_curve.png", SRC)
# 図3：在籍者の顔ぶれ（入会からの月数ごとのヘビーの割合）
mix = MM[MM.ym == months[-1]].groupby("age").type.apply(lambda s: (s == "heavy").mean())
fig, ax = plt.subplots(figsize=(8.5, 3.6))
ax.bar(mix.index, mix.values * 100, color=BLUE)
ax.axhline(40, color=GRAY, ls=":", lw=1)
ax.set_xlabel("入会からの月数（2025年12月に在籍している会員）"); ax.set_ylabel("ヘビーの割合（%）")
ax.set_title("長く在籍している会員ほど、ヘビーが多い（入会時は40%）")
save(fig, "a615_active_mix.png", SRC)
print(json.dumps(out, ensure_ascii=False, indent=1))
