"""792 率の列に「0.05」と「5」が混ざっていると、平均はどれだけずれるのか

架空の割引の記録2,000件。本当の割引率は 0.5%・1%・2%・3%・5%・10%・15%・20%・30% のどれか。
6割はシステムからの入力で割合（5% → 0.05）、4割は手入力で百分率の数（5% → 5）として同じ列に入る。
平均を「そのまま」「1より大きい値だけ100で割る」「入力元で直す」で出し、本当の平均と比べる。
DuckDB（1スレッド）と pandas の一致を確かめる。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import duckdb
from common import RES, SQL, DATA, save, BLUE, ORANGE, GRAY, GREEN, LIGHT

SRC = "出典：架空の割引の記録（作成者が乱数で作成、seed 792）"
rng = np.random.default_rng(792)
N = 2000
LV = np.array([.5, 1, 2, 3, 5, 10, 15, 20, 30])            # 百分率
PR = np.array([.08, .12, .12, .1, .2, .2, .08, .06, .04])
true_pct = rng.choice(LV, N, p=PR)
src = np.where(rng.random(N) < .6, "system", "manual")
val = np.where(src == "system", true_pct / 100, true_pct)
D = pd.DataFrame({"txn_id": np.arange(1, N + 1), "source": src, "discount_rate": np.round(val, 4)})
DATA.mkdir(exist_ok=True); D.to_csv(DATA / "discounts.csv", index=False)

con = duckdb.connect(); con.execute("SET threads=1"); con.register("discounts", D)
q = "\n".join(l for l in (SQL / "02_rate_duckdb.sql").read_text(encoding="utf-8").splitlines() if not l.strip().startswith("--")).strip().rstrip(";")
Q = con.execute(q).df().iloc[0]
v = D.discount_rate.to_numpy()
rule = np.where(v > 1, v / 100, v); bys = np.where(D.source == "manual", v / 100, v)
assert np.isclose(Q.naive_mean, v.mean()) and np.isclose(Q.rule_mean, rule.mean()) and np.isclose(Q.by_source_mean, bys.mean())
true_mean = float(true_pct.mean() / 100)
assert np.isclose(bys.mean(), true_mean)

# 1より大きい値だけ100で割るルールで直らない値
D["true_pct"] = true_pct; D["rule"] = rule
wrong = D[(D.source == "manual") & (D.discount_rate <= 1)]
lv = pd.DataFrame({"true_pct": LV})
lv["manual_rows"] = [int(((D.source == "manual") & (D.true_pct == x)).sum()) for x in LV]
lv["rule_reads_as_pct"] = [x * 100 if x <= 1 else x for x in LV]     # 手入力の値をルールで直したときの読み（%）
lv.to_csv(RES / "by_level.csv", index=False)
# 手入力の割合を変えたときの平均
mix = []
for share in [0, .1, .2, .4, .6, .8, 1.0]:
    s = np.where(rng.random(N) < share, "manual", "system"); vv = np.where(s == "system", true_pct / 100, true_pct)
    mix.append(dict(manual_share=share, naive=vv.mean(), rule=np.where(vv > 1, vv / 100, vv).mean()))
M = pd.DataFrame(mix); M.to_csv(RES / "by_manual_share.csv", index=False)

out = {"rows": N, "manual_rows": int((src == "manual").sum()), "true_mean": true_mean,
       "naive_mean": float(Q.naive_mean), "rule_mean": float(Q.rule_mean), "by_source_mean": float(Q.by_source_mean),
       "naive_ratio": float(Q.naive_mean / true_mean), "rule_gap_pt": float((Q.rule_mean - true_mean) * 100),
       "rule_wrong_rows": int(len(wrong)), "rule_wrong_share_manual": float(len(wrong) / (src == "manual").sum()),
       "rule_wrong_levels": sorted(wrong.true_pct.unique().tolist()),
       "naive_median": float(np.median(v)), "true_median": float(np.median(true_pct) / 100),
       "by_manual_share": M.round(5).to_dict(orient="records"), "duckdb_version": duckdb.__version__}
json.dump(out, open(RES / "a792_main.json", "w"), ensure_ascii=False, indent=1)

# 図1：3通りの平均
fig, ax = plt.subplots(figsize=(8.5, 4.4))
lab = ["そのまま平均", "1より大きい値だけ\n100で割る", "入力元で直す", "本当の平均"]
vals = [Q.naive_mean, Q.rule_mean, Q.by_source_mean, true_mean]
ax.bar(range(4), np.array(vals) * 100, color=[ORANGE, GRAY, BLUE, "#0b0b0b"])
for i, x in enumerate(vals): ax.text(i, x * 100 + .5, f"{x*100:.2f}%" if x < 1 else f"{x*100:.0f}%", ha="center", fontsize=11)
ax.set_yscale("log"); ax.set_xticks(range(4)); ax.set_xticklabels(lab); ax.set_ylabel("割引率の平均（%、対数）")
ax.set_title("0.05 と 5 が混ざった列をそのまま平均すると、本当の平均の何十倍にもなる")
save(fig, "a792_means.png", SRC)

# 図2：書いた値の分布（入力元ごと）
fig, axs = plt.subplots(1, 2, figsize=(10, 4))
for ax, s_, t in [(axs[0], "system", "システムからの入力（割合）"), (axs[1], "manual", "手入力（百分率の数）")]:
    vc = D[D.source == s_].discount_rate.value_counts().sort_index()
    cols = [ORANGE if (s_ == "manual" and x <= 1) else (BLUE if s_ == "system" else GRAY) for x in vc.index]
    ax.bar([f"{x:g}" for x in vc.index], vc.values, color=cols); ax.set_title(t, fontsize=11); ax.tick_params(axis="x", rotation=45)
    ax.set_xlabel("列に入っている値")
axs[0].set_ylabel("件数")
axs[1].set_ylim(0, axs[1].get_ylim()[1] * 1.3)
axs[1].text(.03, .97, f"オレンジの{len(wrong)}件（0.5%と1%）は\n「1より大きい値だけ直す」では直らない", transform=axs[1].transAxes, fontsize=9, va="top")
fig.suptitle("手入力の「0.5」と「1」は、割合の 0.5（50%）・1（100%）と見分けがつかない", y=1.03)
save(fig, "a792_values.png", SRC, y=-0.08)

# 図3：手入力の割合と平均
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.plot(M.manual_share * 100, M.naive * 100, "o-", color=ORANGE, label="そのまま平均")
ax.plot(M.manual_share * 100, M.rule * 100, "o-", color=GRAY, label="1より大きい値だけ100で割る")
ax.axhline(true_mean * 100, color="#0b0b0b", lw=1, ls="--", label="本当の平均")
ax.set_yscale("log"); ax.set_xlabel("手入力（百分率の数）の割合（%）"); ax.set_ylabel("割引率の平均（%、対数）")
ax.legend(frameon=False); ax.set_title("手入力が少しでも混ざると、そのままの平均は大きく外れる")
save(fig, "a792_by_share.png", SRC)
print(json.dumps({k: v for k, v in out.items() if k != "by_manual_share"}, ensure_ascii=False, indent=1)); print(M)
