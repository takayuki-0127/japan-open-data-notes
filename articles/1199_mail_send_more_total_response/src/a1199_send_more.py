"""1199 送る回数を増やすと、1通あたりの反応は下がっても、全体の反応はどう動くのか？（架空のデータ）

作成者が置いた架空の店の会員向けのお知らせのメール。会員10,000人。反応は開封で数える。
1人ひとりの「週1通のときに1通を開く確率」p は平均0.25・標準偏差0.15の0〜1の山形の分布。
週に f 通（1・2・3・4・5・7通）送ると、1通を開く確率は p÷(1＋c×(f−1))（c は飽き、基本0.25）。
1通を受け取るたびに配信を止める（配信停止）確率は u0×(1＋d×(f−1))×(1−p)÷0.75（u0＝0.3%、d＝0.3。開きにくい人ほど止めやすい）。
配信を止めた人は、そのメールまでは受け取り、それ以降は届かない。新しく登録する人は入れない。
(1) 基本の置き方で、送る回数6通り×52週（各20回）
(2) 確かめ：c 3通り×d 3通り×u0 3通り＝27通り（各5回）
"""
import json
import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1199
SRC = "架空の店の会員向けのお知らせのメール（作成者が置いた開く確率・飽き・配信停止からの乱数、seed 1199）"
M = 10000
P_MEAN, P_SD = 0.25, 0.15
C, D, U0 = 0.25, 0.3, 0.003
FREQ = [1, 2, 3, 4, 5, 7]
WEEKS = 52
HOR = [4, 13, 26, 52]
R_MAIN, R_GRID = 20, 5
T0 = time.time()
rng = np.random.default_rng(SEED)


def r(x, d=4):
    return round(float(x), d)


def beta_par(mean, sd):
    k = mean * (1 - mean) / sd ** 2 - 1
    return mean * k, (1 - mean) * k


PA, PB = beta_par(P_MEAN, P_SD)


def simulate(rng, f, c, d, u0, keep=False):
    p = rng.beta(PA, PB, M)
    po = p / (1 + c * (f - 1))
    u = np.minimum(1.0, u0 * (1 + d * (f - 1)) * (1 - p) / (1 - P_MEAN))
    active = np.ones(M, bool)
    w_sent, w_opens, w_active, w_end = [], [], [], []
    left_week = np.full(M, -1)
    opens_person = np.zeros(M, int)
    for w in range(WEEKS):
        n_act = active.sum()
        g = rng.geometric(np.maximum(u, 1e-12))  # 何通目で止めるか
        recv = np.where(active, np.minimum(f, g), 0)
        op = rng.binomial(recv, po)
        stop = active & (g <= f)
        left_week[stop] = w + 1
        active = active & ~stop
        w_sent.append(int(recv.sum()))
        w_opens.append(int(op.sum()))
        w_active.append(int(n_act))
        w_end.append(int(active.sum()))
        opens_person += op
    out = pd.DataFrame({"week": np.arange(1, WEEKS + 1), "members_at_start": w_active, "sent": w_sent, "opens": w_opens, "members_end": w_end})
    if keep:
        return out, pd.DataFrame({"member_id": np.arange(M), "usual_open_prob": np.round(p, 4), "stopped_week": left_week, "opens_52w": opens_person})
    return out


def summarize(ws):
    o = {}
    o["per_mail_w1"] = ws.opens[0] / ws.sent[0]
    o["per_mail_52"] = ws.opens.sum() / ws.sent.sum()
    o["per_mail_w52"] = ws.opens.iloc[-1] / max(ws.sent.iloc[-1], 1)
    for h in HOR:
        o[f"opens_{h}w"] = ws.opens[:h].sum()
    o["weekly_opens_w1"] = ws.opens[0]
    o["weekly_opens_w52"] = ws.opens.iloc[-1]
    o["members_end_13w"] = ws.members_at_start[13]
    o["members_end_26w"] = ws.members_at_start[26]
    o["members_end_52w"] = ws.members_end.iloc[-1]
    return o


# (1) 基本
rows, weekly = [], []
for f in FREQ:
    acc = []
    for rep in range(R_MAIN):
        if f == 3 and rep == 0:
            ws, persons = simulate(rng, f, C, D, U0, keep=True)
            persons.to_csv(DATA / "members_f3.csv", index=False)
        else:
            ws = simulate(rng, f, C, D, U0)
        acc.append(ws)
        s = summarize(ws)
        s.update({"f": f, "rep": rep})
        rows.append(s)
    wk = pd.concat(acc).groupby("week").mean().reset_index()
    wk["f"] = f
    weekly.append(wk)
raw = pd.DataFrame(rows)
tab = raw.groupby("f").mean().drop(columns="rep").reset_index()
weekly = pd.concat(weekly, ignore_index=True)
tab["per_mail_w1_formula"] = [P_MEAN / (1 + C * (f - 1)) for f in FREQ]
tab["weekly_opens_w1_formula"] = [M * f * P_MEAN / (1 + C * (f - 1)) for f in FREQ]
tab = tab.round(4)
for h in HOR:
    tab[f"vs_f1_{h}w"] = (tab[f"opens_{h}w"] / tab[f"opens_{h}w"].iloc[0]).round(4)
tab["per_mail_w1_vs_f1"] = (tab.per_mail_w1 / tab.per_mail_w1.iloc[0]).round(4)
tab["per_mail_52_vs_f1"] = (tab.per_mail_52 / tab.per_mail_52.iloc[0]).round(4)
tab.to_csv(RES / "by_freq.csv", index=False)
weekly.round(2).to_csv(RES / "weekly.csv", index=False)

best = {f"{h}w": int(tab.f[tab[f"opens_{h}w"].idxmax()]) for h in HOR}
# 1週目の、1通あたりの式とのずれ
formula_gap = r(np.max(np.abs(tab.per_mail_w1 - tab.per_mail_w1_formula)))

# 週ごとの1通あたりの開封率（f=1 と f=7）
w1 = weekly[weekly.f == 1]
w7 = weekly[weekly.f == 7]

# (2) 確かめ
grid = []
for c in [0.1, 0.25, 0.5]:
    for d in [0.0, 0.3, 1.0]:
        for u0 in [0.001, 0.003, 0.006]:
            tot = {h: [] for h in HOR}
            pm = []
            for f in FREQ:
                a = {h: 0.0 for h in HOR}
                pmf = 0.0
                for rep in range(R_GRID):
                    ws = simulate(rng, f, c, d, u0)
                    for h in HOR:
                        a[h] += ws.opens[:h].sum() / R_GRID
                    pmf += ws.opens[0] / ws.sent[0] / R_GRID
                for h in HOR:
                    tot[h].append(a[h])
                pm.append(pmf)
            row = {"c": c, "d": d, "u0": u0}
            for h in HOR:
                row[f"best_f_{h}w"] = FREQ[int(np.argmax(tot[h]))]
                row[f"f7_over_f1_{h}w"] = r(tot[h][-1] / tot[h][0])
            row["per_mail_f7_over_f1_w1"] = r(pm[-1] / pm[0])
            grid.append(row)
grid = pd.DataFrame(grid)
grid.to_csv(RES / "grid.csv", index=False)

robust = {"n": len(grid)}
for h in HOR:
    robust[f"best_f_{h}w_counts"] = {str(k): int(v) for k, v in grid[f"best_f_{h}w"].value_counts().sort_index().items()}
    robust[f"f7_over_f1_{h}w_min"] = r(grid[f"f7_over_f1_{h}w"].min())
    robust[f"f7_over_f1_{h}w_max"] = r(grid[f"f7_over_f1_{h}w"].max())
robust["best_shrinks_or_same_share"] = r(np.mean(grid.best_f_52w <= grid.best_f_4w) * 100, 2)
robust["best_shrinks_strict_share"] = r(np.mean(grid.best_f_52w < grid.best_f_4w) * 100, 2)
robust["f7_below_f1_52w_count"] = int((grid.f7_over_f1_52w < 1).sum())
robust["per_mail_f7_over_f1_w1_range"] = [r(grid.per_mail_f7_over_f1_w1.min()), r(grid.per_mail_f7_over_f1_w1.max())]
robust["d0_best_52w_counts"] = {str(k): int(v) for k, v in grid[grid.d == 0].best_f_52w.value_counts().sort_index().items()}
robust["c05_best_4w_counts"] = {str(k): int(v) for k, v in grid[grid.c == 0.5].best_f_4w.value_counts().sort_index().items()}

pf3 = pd.read_csv(DATA / "members_f3.csv")
res = {
    "settings": {"members": M, "usual_open_mean": P_MEAN, "usual_open_sd": P_SD, "fatigue_c": C, "stop_d": D, "stop_u0": U0,
                 "freq_per_week": FREQ, "weeks": WEEKS, "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
    "by_freq": tab.to_dict(orient="records"),
    "best_f_by_horizon": best,
    "per_mail_w1_formula_max_gap": formula_gap,
    "weekly_per_mail": {"f1_w1": r(w1.opens.iloc[0] / w1.sent.iloc[0]), "f1_w52": r(w1.opens.iloc[-1] / w1.sent.iloc[-1]),
                        "f7_w1": r(w7.opens.iloc[0] / w7.sent.iloc[0]), "f7_w52": r(w7.opens.iloc[-1] / w7.sent.iloc[-1]),
                        
                        "f1_weekly_opens_w52": r(w1.opens.iloc[-1], 1), "f7_weekly_opens_w52": r(w7.opens.iloc[-1], 1),
                        "f1_weekly_opens_w1": r(w1.opens.iloc[0], 1), "f7_weekly_opens_w1": r(w7.opens.iloc[0], 1)},
    "example_f3": {"stopped_share": r(np.mean(pf3.stopped_week > 0)),
                   "usual_open_stopped": r(pf3.usual_open_prob[pf3.stopped_week > 0].mean()),
                   "usual_open_stayed": r(pf3.usual_open_prob[pf3.stopped_week < 0].mean())},
    "robust": robust,
}

# 図1：1通あたりの開封率と、全体の開封数（13週・52週）
fig, axs = plt.subplots(1, 2, figsize=(9.6, 4.2))
xs = [str(f) for f in FREQ]
b = axs[0].bar(xs, tab.per_mail_52 * 100, color=GRAY, width=0.6)
for bb, v in zip(b, tab.per_mail_52 * 100):
    axs[0].text(bb.get_x() + bb.get_width() / 2, v, f"{v:.2f}%", ha="center", va="bottom", fontsize=9)
axs[0].set_title("1通あたりの開封率（52週の合計で割る）", fontsize=11)
axs[0].set_xlabel("週に送る通数")
axs[0].set_ylabel("%")
axs[0].set_ylim(0, 30)
w = 0.38
xi = np.arange(len(FREQ))
v13 = tab.opens_13w / 1000
v52 = tab.opens_52w / 1000
b1 = axs[1].bar(xi - w / 2, v13, w, color=LIGHT, label="はじめの13週")
b2 = axs[1].bar(xi + w / 2, v52, w, color=BLUE, label="52週")
for bb, v in list(zip(b1, v13)) + list(zip(b2, v52)):
    axs[1].text(bb.get_x() + bb.get_width() / 2, v, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
axs[1].set_xticks(xi)
axs[1].set_xticklabels(xs)
axs[1].set_title("開封の合計（千回）", fontsize=11)
axs[1].set_xlabel("週に送る通数")
axs[1].set_ylim(0, max(v52) * 1.18)
axs[1].legend(fontsize=9, frameon=False, loc="upper left")
fig.suptitle("会員10,000人、基本の置き方（20回の平均）", fontsize=12)
fig.tight_layout()
save(fig, "a1199_per_mail_vs_total.png", SRC)

# 図2：週ごとの開封数
fig, ax = plt.subplots(figsize=(7.4, 4.4))
cmap = {1: GRAY, 2: LIGHT, 3: BLUE, 5: GREEN, 7: ORANGE}
for f in [1, 2, 3, 5, 7]:
    wk = weekly[weekly.f == f]
    ax.plot(wk.week, wk.opens, color=cmap[f], lw=2, label=f"週{f}通")
ax.set_xlabel("週")
ax.set_ylabel("その週の開封の数")
ax.set_ylim(0, None)
ax.set_title("週ごとの開封の数（配信を止める人が積み重なる）")
ax.legend(fontsize=9, frameon=False, loc="upper right")
save(fig, "a1199_weekly.png", SRC)

# 図3：確かめ（数える週の長さごとの、いちばん開封の多い通数）
fig, ax = plt.subplots(figsize=(7.4, 4.4))
mat = np.zeros((len(FREQ), len(HOR)))
for j, h in enumerate(HOR):
    vc = grid[f"best_f_{h}w"].value_counts()
    for i, f in enumerate(FREQ):
        mat[i, j] = vc.get(f, 0)
bottom = np.zeros(len(HOR))
fcol = {1: GRAY, 2: LIGHT, 3: BLUE, 4: INK, 5: GREEN, 7: ORANGE}
for i, f in enumerate(FREQ):
    ax.bar([f"{h}週" for h in HOR], mat[i], bottom=bottom, color=fcol[f], label=f"週{f}通", width=0.6)
    for j in range(len(HOR)):
        if mat[i, j] > 0:
            ax.text(j, bottom[j] + mat[i, j] / 2, f"{int(mat[i, j])}", ha="center", va="center", fontsize=9, color="white" if f in (3, 4, 7) else INK)
    bottom += mat[i]
ax.set_ylabel("置き方の数（27通りのうち）")
ax.set_xlabel("開封を合計する週の長さ")
ax.set_ylim(0, 27)
ax.set_title("開封の合計がいちばん多くなる、週に送る通数")
ax.legend(fontsize=9, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1.0))
save(fig, "a1199_grid_best.png", SRC)

with open(RES / "a1199_main.json", "w", encoding="utf-8") as fo:
    json.dump(res, fo, ensure_ascii=False, indent=1)
print(tab.T.to_string())
print(best, formula_gap)
print(json.dumps(res["weekly_per_mail"], ensure_ascii=False), res["example_f3"])
print(json.dumps(robust, ensure_ascii=False))
print("sec", round(time.time() - T0, 1))
