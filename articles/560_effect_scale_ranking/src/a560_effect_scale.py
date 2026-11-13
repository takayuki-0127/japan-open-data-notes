"""560 効果を「差」で見るか「比」で見るかで、効果の大きい層が入れ替わるのはなぜか（正解の分かるデータで試す）

架空の顧客を、クーポンなしの購入率が違う6つの層に分ける（2%〜60%）。クーポンの本当の効き方を
「オッズ比が一定」「率の比が一定」「率の差が一定」の3通りに置き、率の差・率の比・オッズ比で層の順位を比べる。
各層・各群3,000人を引いて、順位の当たり方と、層で効き方が違うか（異質性）の検定結果も数える。
"""
import json
import numpy as np, pandas as pd
import duckdb
from scipy import stats
import matplotlib.pyplot as plt
from common import save, RES, SQL, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED, M, REPS = 560, 3000, 1000
rng = np.random.default_rng(SEED)
SRC = "架空のデータ（作成者が乱数で作成、seed 560）"
SEG = ["S1", "S2", "S3", "S4", "S5", "S6"]
P0 = np.array([0.02, 0.05, 0.10, 0.20, 0.40, 0.60])          # クーポンなしの購入率


def p1_of(p0, truth):
    if truth == "OR":   # オッズ比 1.8 で一定
        o = p0 / (1 - p0) * 1.8; return o / (1 + o)
    if truth == "RR":   # 率の比 1.3 で一定
        return p0 * 1.3
    return p0 + 0.04    # 率の差 +4ポイントで一定


def measures(p0, p1):
    return dict(rd=p1 - p0, rr=p1 / p0, orr=(p1 / (1 - p1)) / (p0 / (1 - p0)))


def rank_desc(v):
    return pd.Series(np.round(v, 9)).rank(ascending=False, method="min").astype(int).to_numpy()   # 同じ値は同順位


def is_const(v):
    return np.ptp(np.round(v, 9)) == 0


# ---- 1. 本当の値と順位
rows = []
for truth in ["OR", "RR", "RD"]:
    p1 = p1_of(P0, truth); m = measures(P0, p1)
    for k in ["rd", "rr", "orr"]:
        for s, v, r in zip(SEG, m[k], rank_desc(m[k])):
            rows.append(dict(truth=truth, measure=k, segment=s, p0=P0[SEG.index(s)], p1=p1[SEG.index(s)], value=v, rank=r))
true_tab = pd.DataFrame(rows); true_tab.round(5).to_csv(RES / "true_values.csv", index=False)


def homog(est, var):
    w = 1 / var; bar = (w * est).sum() / w.sum(); chi = (w * (est - bar) ** 2).sum()
    return stats.chi2.sf(chi, len(est) - 1)


# ---- 2. 各層・各群 3,000人を引く
rows = []
for truth in ["OR", "RR", "RD"]:
    p1 = p1_of(P0, truth); tm = measures(P0, p1)
    top_true = {k: int(np.argmax(tm[k])) for k in ["rd", "rr", "orr"]}
    hits = {k: 0 for k in top_true}; sig_rd = sig_lor = 0; same_top_rd_rr = 0
    for _ in range(REPS):
        a = rng.binomial(M, p1); c = rng.binomial(M, P0)              # 購入した人数（あり／なし）
        q1, q0 = (a + 0.5) / (M + 1), (c + 0.5) / (M + 1)              # 0 を避けるため 0.5 を足す
        m = measures(q0, q1)
        for k in hits: hits[k] += int(np.argmax(m[k]) == top_true[k])
        same_top_rd_rr += int(np.argmax(m["rd"]) == np.argmax(m["rr"]))
        v_rd = q1 * (1 - q1) / M + q0 * (1 - q0) / M
        v_lor = 1 / (a + 0.5) + 1 / (M - a + 0.5) + 1 / (c + 0.5) + 1 / (M - c + 0.5)
        sig_rd += homog(m["rd"], v_rd) < 0.05; sig_lor += homog(np.log(m["orr"]), v_lor) < 0.05
    hit = {k: (np.nan if is_const(tm[k]) else hits[k] / REPS) for k in hits}   # 本当の値が一定の尺度は「最も効く層」がない
    rows.append(dict(truth=truth, top_hit_rd=hit["rd"], top_hit_rr=hit["rr"], top_hit_or=hit["orr"],
                     same_top_rd_rr=same_top_rd_rr / REPS, sig_hetero_rd=sig_rd / REPS, sig_hetero_logor=sig_lor / REPS))
sim = pd.DataFrame(rows); sim.round(4).to_csv(RES / "simulation.csv", index=False)

# ---- 3. 例の1回（オッズ比一定）と SQL の確認
p1 = p1_of(P0, "OR")
recs = []
for i, s in enumerate(SEG):
    for arm, p in [(1, p1[i]), (0, P0[i])]:
        k = rng.binomial(M, p); recs.append(dict(segment=s, coupon=arm, n_customers=M, n_buyers=int(k)))
ex = pd.DataFrame(recs); ex.to_csv(RES / "example_counts_OR.csv", index=False)
con = duckdb.connect(config={"threads": 1}); con.register("counts", pd.read_csv(RES / "example_counts_OR.csv"))
sq = con.execute(open(SQL / "a560_effect_scale.sql", encoding="utf-8").read()).df(); sq.to_csv(RES / "sql_example_OR.csv", index=False)
w = ex.pivot(index="segment", columns="coupon", values="n_buyers") / M
py = pd.DataFrame({"rd": w[1] - w[0], "rr": w[1] / w[0], "orr": (w[1] / (1 - w[1])) / (w[0] / (1 - w[0]))})
sq2 = sq.set_index("segment").loc[py.index]
sql_check = dict(rd_match=bool(np.allclose(py.rd, sq2.rate_diff)), rr_match=bool(np.allclose(py.rr, sq2.rate_ratio)),
                 or_match=bool(np.allclose(py.orr, sq2.odds_ratio)),
                 rank_rd=sq2.rank_diff.tolist(), rank_rr=sq2.rank_ratio.tolist(), rank_or=sq2.rank_odds.tolist())
# クーポン1万枚を配るとき、増える購入の数（本当の値・オッズ比一定）
tm = measures(P0, p1); extra = 10000 * tm["rd"]
json.dump(dict(p0=P0.tolist(), M=M, reps=REPS, sql_check=sql_check, extra_buyers_per_10000=dict(zip(SEG, extra.round(1))),
               truth_OR=dict(rd=tm["rd"].round(4).tolist(), rr=tm["rr"].round(3).tolist(), orr=tm["orr"].round(3).tolist())),
          open(RES / "a560_main.json", "w"), ensure_ascii=False, indent=1, default=float)

# ---- 図1：オッズ比一定のとき、3つの尺度での層の順位
lab = [f"{s}\n（{p:.0%}）" for s, p in zip(SEG, P0)]
fig, ax = plt.subplots(1, 3, figsize=(12, 4))
for a, (k, ttl, fmt, c) in zip(ax, [("rd", "率の差（ポイント）", lambda v: f"{v*100:.1f}", ORANGE), ("rr", "率の比", lambda v: f"{v:.2f}", BLUE), ("orr", "オッズ比", lambda v: f"{v:.2f}", GREEN)]):
    v = tm[k] * (100 if k == "rd" else 1); r = rank_desc(tm[k])
    a.bar(range(6), v, color=c, alpha=0.8)
    for i in range(6): a.text(i, v[i], fmt(tm[k][i]) + ("" if is_const(tm[k]) else f"\n{r[i]}位"), ha="center", va="bottom", fontsize=8.5)
    if is_const(tm[k]): a.text(2.5, v.max() * 1.18, "全層同じ（順位なし）", ha="center", fontsize=9.5)
    a.set_xticks(range(6), lab, fontsize=8.5); a.set_title(ttl); a.set_ylim(0, v.max() * 1.3)
ax[0].set_ylabel("クーポンの効果"); ax[1].set_xlabel("層（クーポンなしの購入率）")
fig.suptitle("本当の効き方は「オッズ比1.8で一定」。同じ効き方を3つの尺度で見ると", y=1.02, fontsize=12)
save(fig, "a560_three_scales.png", SRC + "。本当の値")

# ---- 図2：もとの率と、効果の大きさ（3通りの本当の効き方）
xs = np.linspace(0.01, 0.75, 200)
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4))
for truth, c, lb in [("OR", GREEN, "オッズ比1.8で一定"), ("RR", BLUE, "率の比1.3で一定"), ("RD", ORANGE, "率の差+4ポイントで一定")]:
    m = measures(xs, p1_of(xs, truth))
    ax[0].plot(xs * 100, m["rd"] * 100, color=c, label=lb); ax[1].plot(xs * 100, m["rr"], color=c, label=lb)
for a in ax:
    for p in P0: a.axvline(p * 100, color=GRAY, lw=0.6, ls=":")
    a.set_xlabel("クーポンなしの購入率（%）")
ax[0].set_ylabel("率の差（ポイント）"); ax[1].set_ylabel("率の比"); ax[1].set_ylim(0.9, 2.2)
ax[0].set_title("率の差で見ると"); ax[1].set_title("率の比で見ると"); ax[0].legend(frameon=False, fontsize=8.5)
save(fig, "a560_curves.png", SRC + "。点線は6つの層のもとの率")

# ---- 図3：層で効き方が違うか（異質性の検定）と、最も効く層の当たり
fig, ax = plt.subplots(1, 2, figsize=(10.5, 4))
tl = ["オッズ比\nで一定", "率の比\nで一定", "率の差\nで一定"]; x = np.arange(3); w2 = 0.36
ax[0].bar(x - w2 / 2, sim.sig_hetero_rd, w2, color=ORANGE, label="率の差で検定"); ax[0].bar(x + w2 / 2, sim.sig_hetero_logor, w2, color=GREEN, label="オッズ比で検定")
for i in range(3):
    ax[0].text(i - w2 / 2, sim.sig_hetero_rd[i] + 0.02, f"{sim.sig_hetero_rd[i]:.0%}", ha="center", fontsize=8.5)
    ax[0].text(i + w2 / 2, sim.sig_hetero_logor[i] + 0.02, f"{sim.sig_hetero_logor[i]:.0%}", ha="center", fontsize=8.5)
ax[0].set_xticks(x, tl, fontsize=9); ax[0].set_ylim(0, 1.32); ax[0].set_ylabel("「層で効き方が違う」が p<0.05 になった割合")
ax[0].set_title("同じデータで、異質性の答えが割れる"); ax[0].legend(frameon=False, fontsize=8.5, loc="upper center", ncol=2)
ax[0].set_xlabel("本当の効き方")
o = sim[sim.truth == "OR"].iloc[0]; hv = [o.top_hit_rd, o.top_hit_rr]
ax[1].bar([0, 1], hv, 0.5, color=[ORANGE, BLUE])
for i in range(2): ax[1].text(i, hv[i] + 0.02, f"{hv[i]:.0%}", ha="center", fontsize=9)
ax[1].set_xticks([0, 1], ["率の差\n（本当の1位は S5）", "率の比\n（本当の1位は S1）"], fontsize=9); ax[1].set_ylim(0, 1.12); ax[1].set_xlim(-0.6, 1.6)
ax[1].set_ylabel("本当の1位を当てた割合"); ax[1].set_title("オッズ比一定のとき、「最も効く層」を当てた割合")
save(fig, "a560_hetero.png", SRC + f"。各層・各群{M:,}人×{REPS:,}回")
print(true_tab[true_tab.truth == "OR"].pivot(index="segment", columns="measure", values=["value", "rank"]).round(3)); print(sim.round(3).to_string()); print(sql_check); print(extra.round(1))
