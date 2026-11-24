"""1197 開封率で選ぶかクリック率で選ぶかで、良い件名は入れかわるのか？（架空のデータ）

作成者が置いた架空の店の会員向けのお知らせのメール。
会員20,000人。1人ひとりの「ふだんの開く確率」p は平均0.22・標準偏差0.12の0〜1の山形の分布から置く。
件名 i には「開かせる強さ」a_i と「開いた人を押させる強さ」b_i を置く。
  件名 i を受け取った人が開く確率＝ p の見かけの強さ（ロジット）に a_i を足したもの
  開いた人がリンクを押す確率 q_i ＝ 0.10 × exp(b_i)（0.9で上限）
  a_i は平均0・標準偏差0.3、b_i は平均0・標準偏差 sb（基本0.3）の正規分布。2つの相関 rho（基本 −0.5：開かせる件名ほど、開いた人が押しにくい）。
本当の開封率＝会員全体で開く確率を平均した値。本当のクリック率（送った数あたり）＝本当の開封率×q_i。
1回の配信で件名を K 個（基本6）試し、それぞれ n 通（基本2,000通）を会員からでたらめに選んで送る。
  開封率＝開いた数÷送った数、クリック率＝押した人の数÷送った数、開いた人のクリック率＝押した人÷開いた数。
「良い件名」は、本当のクリック率（送った数あたり）がいちばん高い件名と作成者が決めた。
(1) 基本の置き方で配信を3,000回
(2) 確かめ：rho 4通り×n 3通り×K 3通り×sb 3通り＝108通り（各500回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN

SEED = 1197
SRC = "架空の店の会員向けのお知らせのメール（作成者が置いた開く確率と件名の強さからの乱数、seed 1197）"
M = 20000
P_MEAN, P_SD = 0.22, 0.12
Q0 = 0.10
RHO, N, K, SA, SB = -0.5, 2000, 6, 0.3, 0.3
R_MAIN, R_GRID = 3000, 500
GRID_RHO = [-0.7, -0.4, 0.0, 0.4]
GRID_N = [500, 2000, 10000]
GRID_K = [2, 6, 10]
GRID_SB = [0.1, 0.3, 0.5]
T0 = time.time()
rng = np.random.default_rng(SEED)


def r(x, d=4):
    return round(float(x), d)


def beta_par(mean, sd):
    k = mean * (1 - mean) / sd ** 2 - 1
    return mean * k, (1 - mean) * k


# 会員
pa, pb = beta_par(P_MEAN, P_SD)
p = rng.beta(pa, pb, M)
lp = np.log(p / (1 - p))
A_GRID = np.round(np.arange(-3.0, 3.0001, 0.001), 3)
F_GRID = np.array([np.mean(1 / (1 + np.exp(-(lp + a)))) for a in A_GRID])


def true_open(a):
    return np.interp(a, A_GRID, F_GRID)


def draw_subjects(rng, R, K, rho, sb):
    z1 = rng.standard_normal((R, K))
    z2 = rng.standard_normal((R, K))
    a = SA * z1
    b = sb * (rho * z1 + np.sqrt(1 - rho ** 2) * z2)
    return a, b


def run(rng, R, K, n, rho, sb):
    a, b = draw_subjects(rng, R, K, rho, sb)
    to = true_open(a)
    q = np.minimum(0.9, Q0 * np.exp(b))
    tc = to * q
    op = rng.binomial(n, to)
    cl = rng.binomial(op, q)
    o_rate, c_rate = op / n, cl / n
    cpo = np.where(op > 0, cl / np.maximum(op, 1), 0)
    rows = np.arange(R)
    best = tc.argmax(1)
    pick = {"open": o_rate.argmax(1), "click": c_rate.argmax(1), "cpo": cpo.argmax(1)}
    out = {
        "mismatch_obs": float(np.mean(pick["open"] != pick["click"])),
        "mismatch_true": float(np.mean(to.argmax(1) != tc.argmax(1))),
        "mismatch_obs_cpo": float(np.mean(pick["click"] != pick["cpo"])),
        "mean_open": float(o_rate.mean()), "mean_click": float(c_rate.mean()),
    }
    out["mean_clicks_per_subject"] = float(cl.mean())
    for k, idx in pick.items():
        out[f"hit_{k}"] = float(np.mean(idx == best))
        out[f"loss_{k}"] = float(np.mean(1 - tc[rows, idx] / tc[rows, best]))
        out[f"miss_{k}"] = 1 - out[f"hit_{k}"]
    # 本当の開封率いちばんの件名を選んだときの損（ぶれなし、作りどおりの分）
    tb = to.argmax(1)
    out["loss_true_open"] = float(np.mean(1 - tc[rows, tb] / tc[rows, best]))
    out["hit_true_open"] = float(np.mean(tb == best))
    # 開封率いちばんの件名の、開いた人のクリック率は6件名の中で何位か（本当の値）
    q_rank = (q[:, :, None] > q[:, None, :]).sum(2)  # 自分より低い数
    out["open_winner_q_from_top"] = float(np.mean(K - q_rank[rows, pick["open"]]))
    return out, dict(a=a, b=b, to=to, q=q, tc=tc, op=op, cl=cl, pick=pick, best=best)


# (1) 基本
main, det = run(rng, R_MAIN, K, N, RHO, SB)

# 例：1回分を1人ずつ送る形で作る（data）
ex_rng = np.random.default_rng(SEED + 1)
ea, eb = draw_subjects(ex_rng, 1, K, RHO, SB)
ea, eb = ea[0], eb[0]
eq = np.minimum(0.9, Q0 * np.exp(eb))
recs = []
ids = ex_rng.choice(M, size=K * N, replace=False)
for i in range(K):
    who = ids[i * N:(i + 1) * N]
    po = 1 / (1 + np.exp(-(lp[who] + ea[i])))
    o = ex_rng.random(N) < po
    c = o & (ex_rng.random(N) < eq[i])
    recs.append(pd.DataFrame({"member_id": who, "subject": f"件名{i + 1}", "usual_open_prob": np.round(p[who], 4),
                              "opened": o.astype(int), "clicked": c.astype(int)}))
ex = pd.concat(recs, ignore_index=True)
ex.to_csv(DATA / "example_campaign.csv", index=False)
ex_sum = ex.groupby("subject", sort=False).agg(sent=("opened", "size"), opens=("opened", "sum"), clicks=("clicked", "sum")).reset_index()
ex_sum["open_rate"] = (ex_sum.opens / ex_sum.sent).round(4)
ex_sum["click_rate"] = (ex_sum.clicks / ex_sum.sent).round(4)
ex_sum["click_per_open"] = (ex_sum.clicks / ex_sum.opens).round(4)
ex_sum["true_open_rate"] = np.round(true_open(ea), 4)
ex_sum["true_click_per_open"] = np.round(eq, 4)
ex_sum["true_click_rate"] = np.round(true_open(ea) * eq, 4)
ex_sum.to_csv(RES / "example_subjects.csv", index=False)

# 1人ずつ送る形と、二項（まとめて引く）形が合うかの確かめ：例の6件名を1人ずつ200回
chk_rng = np.random.default_rng(SEED + 2)
acc = np.zeros(K)
for _ in range(200):
    for i in range(K):
        who = chk_rng.choice(M, size=N, replace=False)
        po = 1 / (1 + np.exp(-(lp[who] + ea[i])))
        acc[i] += np.mean(chk_rng.random(N) < po)
chk_gap = float(np.max(np.abs(acc / 200 - true_open(ea))))

# (2) 確かめ
grid = []
for rho in GRID_RHO:
    for n in GRID_N:
        for k in GRID_K:
            for sb in GRID_SB:
                o, _ = run(rng, R_GRID, k, n, rho, sb)
                grid.append({"rho": rho, "n": n, "K": k, "sb": sb, **{kk: r(v) for kk, v in o.items()}})
grid = pd.DataFrame(grid)
grid.to_csv(RES / "grid.csv", index=False)

# 基本の置き方で rho だけを変えた行（n=2000, K=6, s=0.3）
g0 = grid[(grid.n == 2000) & (grid.K == 6) & (grid.sb == 0.3)]
k6 = grid[grid.K == 6]
robust = {
    "n": len(grid),
    "mismatch_obs_min": r(grid.mismatch_obs.min()), "mismatch_obs_max": r(grid.mismatch_obs.max()),
    "mismatch_true_min": r(grid.mismatch_true.min()), "mismatch_true_max": r(grid.mismatch_true.max()),
    "by_rho_base": [{"rho": float(x.rho), "mismatch_obs": float(x.mismatch_obs), "mismatch_true": float(x.mismatch_true),
                     "loss_open": float(x.loss_open), "loss_click": float(x.loss_click)} for x in g0.itertuples()],
    "rho0_mismatch_obs_min": r(grid[grid.rho == 0].mismatch_obs.min()),
    "rho0_mismatch_obs_max": r(grid[grid.rho == 0].mismatch_obs.max()),
    "rhoneg_mismatch_true_min": r(grid[grid.rho < 0].mismatch_true.min()),
    "rhoneg_mismatch_true_max": r(grid[grid.rho < 0].mismatch_true.max()),
    "rhopos_mismatch_true_max": r(grid[grid.rho > 0].mismatch_true.max()),
    "loss_open_min": r(grid.loss_open.min()), "loss_open_max": r(grid.loss_open.max()),
    "loss_click_min": r(grid.loss_click.min()), "loss_click_max": r(grid.loss_click.max()),
    "share_click_better": r(np.mean(grid.loss_click < grid.loss_open) * 100, 2),
    "share_click_better_rhoneg": r(np.mean((grid.loss_click < grid.loss_open)[grid.rho < 0]) * 100, 2),
    "open_better_count_by_sb": [{"sb": sb, "count": int(((grid.loss_open < grid.loss_click) & (grid.sb == sb)).sum()), "of": int((grid.sb == sb).sum())} for sb in GRID_SB],
    "by_n_k6_s03_rhom04": [{"n": int(x.n), "mismatch_obs": float(x.mismatch_obs), "hit_click": float(x.hit_click), "hit_open": float(x.hit_open)}
                           for x in grid[(grid.K == 6) & (grid.sb == 0.3) & (grid.rho == -0.4)].itertuples()],
    "by_sb": [{"sb": sb, "mismatch_true_min": r(grid[grid.sb == sb].mismatch_true.min()), "mismatch_true_max": r(grid[grid.sb == sb].mismatch_true.max()),
               "mismatch_obs_min": r(grid[grid.sb == sb].mismatch_obs.min()), "mismatch_obs_max": r(grid[grid.sb == sb].mismatch_obs.max()),
               "loss_open_min": r(grid[grid.sb == sb].loss_open.min()), "loss_open_max": r(grid[grid.sb == sb].loss_open.max()),
               "loss_click_min": r(grid[grid.sb == sb].loss_click.min()), "loss_click_max": r(grid[grid.sb == sb].loss_click.max())} for sb in GRID_SB],
    "k2_mismatch_obs_range": [r(grid[grid.K == 2].mismatch_obs.min()), r(grid[grid.K == 2].mismatch_obs.max())],
    "k10_mismatch_obs_range": [r(grid[grid.K == 10].mismatch_obs.min()), r(grid[grid.K == 10].mismatch_obs.max())],
}

res = {
    "settings": {"members": M, "usual_open_mean": P_MEAN, "usual_open_sd": P_SD, "click_per_open_base": Q0,
                 "rho": RHO, "sent_per_subject": N, "subjects": K, "open_strength_sd": SA, "click_strength_sd": SB,
                 "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
    "main": {k: r(v) for k, v in main.items()},
    "example": ex_sum.to_dict(orient="records"),
    "check_person_vs_bulk_max_gap": r(chk_gap, 5),
    "robust": robust,
}
res["run_sec"] = round(time.time() - T0, 1)

# 図1：例の1回分
fig, ax = plt.subplots(figsize=(6.6, 4.6))
ax.scatter(ex_sum.open_rate * 100, ex_sum.click_rate * 100, s=70, color=BLUE, zorder=3)
for t in ex_sum.itertuples():
    ax.annotate(t.subject, (t.open_rate * 100, t.click_rate * 100), xytext=(6, 4), textcoords="offset points", fontsize=10, color=INK)
io, ic = ex_sum.open_rate.idxmax(), ex_sum.click_rate.idxmax()
ax.scatter([ex_sum.open_rate[io] * 100], [ex_sum.click_rate[io] * 100], s=230, facecolors="none", edgecolors=ORANGE, linewidths=2, label="開封率がいちばん高い件名")
ax.scatter([ex_sum.open_rate[ic] * 100], [ex_sum.click_rate[ic] * 100], s=230, marker="s", facecolors="none", edgecolors=GREEN, linewidths=2, label="クリック率がいちばん高い件名")
ax.set_xlabel("開封率（開いた数÷送った数、%）")
ax.set_ylabel("クリック率（押した人÷送った数、%）")
ax.set_title("例の1回分：件名6つ、各2,000通")
ax.legend(fontsize=9, loc="lower right", frameon=False)
save(fig, "a1197_example.png", SRC)

# 図2：選び方ごとの当たりと損（基本）
fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.0))
lab = ["開封率で選ぶ", "クリック率で選ぶ", "開いた人の\nクリック率で選ぶ"]
hits = [main["hit_open"] * 100, main["hit_click"] * 100, main["hit_cpo"] * 100]
loss = [main["loss_open"] * 100, main["loss_click"] * 100, main["loss_cpo"] * 100]
for ax, v, t, fmt in [(axs[0], hits, "良い件名を選べた割合（%）", "{:.2f}%"), (axs[1], loss, "選んだ件名のクリック率が\nいちばん良い件名より低い分（平均、%）", "{:.2f}%")]:
    bars = ax.bar(lab, v, color=[ORANGE, GREEN, GRAY], width=0.6)
    for bb, x in zip(bars, v):
        ax.text(bb.get_x() + bb.get_width() / 2, x, fmt.format(x), ha="center", va="bottom", fontsize=10)
    ax.set_ylim(0, max(v) * 1.2)
    ax.set_title(t, fontsize=11)
    ax.tick_params(axis="x", labelsize=9)
fig.suptitle("基本の置き方（相関−0.5・件名6つ・各2,000通、3,000回）", fontsize=12)
fig.tight_layout()
save(fig, "a1197_pick.png", SRC)

# 図3：相関ごとの入れかわり（K=6, s=0.3）
fig, ax = plt.subplots(figsize=(6.8, 4.4))
cols = {500: GRAY, 2000: BLUE, 10000: INK}
for n in GRID_N:
    g = grid[(grid.n == n) & (grid.K == 6) & (grid.sb == 0.3)]
    ax.plot(g.rho, g.mismatch_obs * 100, "o-", color=cols[n], label=f"数えた値（各{n:,}通）")
gt = grid[(grid.n == 2000) & (grid.K == 6) & (grid.sb == 0.3)]
ax.plot(gt.rho, gt.mismatch_true * 100, "s--", color=ORANGE, label="本当の値どうし（ぶれなし）")
ax.set_xlabel("件名の「開かせる強さ」と「押させる強さ」の相関（置いた値）")
ax.set_ylabel("開封率1位とクリック率1位が\n違う件名だった配信（%）")
ax.set_ylim(0, 100)
ax.set_xticks(GRID_RHO)
ax.set_title("件名6つ・押させる強さの散らばり0.3のとき")
ax.legend(fontsize=9, frameon=False)
save(fig, "a1197_by_rho.png", SRC)

with open(RES / "a1197_main.json", "w", encoding="utf-8") as f:
    res.pop("run_sec")
    json.dump(res, f, ensure_ascii=False, indent=1)
print(json.dumps(res["main"], ensure_ascii=False))
print(ex_sum)
print("chk", chk_gap, "sec", round(time.time() - T0, 1))
