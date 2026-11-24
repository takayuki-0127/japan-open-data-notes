"""1198 届かなかったアドレスを分母に残すか除くかで、開封率はどう変わるのか？（架空のデータ）

作成者が置いた架空の6店（A店〜F店）の会員向けのお知らせのメール。各店の会員リストは5,000アドレス。
登録してからの月数は、店ごとに 0〜L か月の一様（L＝6・12・24・36・60・96）。古いリストほど登録の古い人が多い。
アドレスは1か月あたり h（基本1%）の割合で使われなくなり、送ると「宛先なし」で戻る（ハードバウンス）。
戻らないアドレスのうち、1か月あたり z（基本1.5%）の割合で、受け取りはするが持ち主がもう読まない「放置」になる。
送るたびに、一時的に届かない（ソフトバウンス：受信箱がいっぱいなど）割合は、読む人のアドレスで2%、放置のアドレスで v（基本20%）。
読む人1人ひとりの開く確率は、店ごとの平均 m（A〜F＝0.26・0.28・0.30・0.32・0.34・0.36、古いリストの店ほど高い）・標準偏差0.15の0〜1の山形の分布。
開封率の4つの分母：
 ① 送った数　② 送った数−ハードバウンス　③ 届いた数（②からソフトバウンスも除く）
 ④ 届いた読む人の数（放置を除く。実際の記録では分からない。作成者が置いた本当の値）
(1) 6店×各200回（リストを作り直す）
(2) 月ごとの例：C店のリストを12か月送る。毎月100人が新しく登録。1〜6か月目は戻ったアドレスを消さず、7か月目の配信のあとから毎月消す
(3) 確かめ：h 3通り×z 3通り×v 2通り×店どうしの開く確率の差 2通り（隣どうし0.01・0.02）×開く確率の割り当て2通り（古いリストほど高い・店にでたらめに割り当てる）＝72通り（各100回）
"""
import json
import time
from itertools import combinations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, GREEN, LIGHT

SEED = 1198
SRC = "架空の6店の会員向けのお知らせのメール（作成者が置いたアドレスの古び方と開く確率からの乱数、seed 1198）"
SHOPS = ["A店", "B店", "C店", "D店", "E店", "F店"]
L = [6, 12, 24, 36, 60, 96]
M_BASE = [0.26, 0.28, 0.30, 0.32, 0.34, 0.36]
NADDR = 5000
H, Z, V, SOFT_ACTIVE, SD = 0.01, 0.015, 0.20, 0.02, 0.15
R_MAIN, R_GRID = 200, 100
T0 = time.time()
rng = np.random.default_rng(SEED)


def r(x, d=4):
    return round(float(x), d)


def beta_par(mean, sd):
    k = mean * (1 - mean) / sd ** 2 - 1
    return mean * k, (1 - mean) * k


def make_list(rng, Lmax, m, h, z, n=NADDR):
    age = rng.uniform(0, Lmax, n)
    dead = rng.random(n) < 1 - np.exp(-h * age)
    aband = (~dead) & (rng.random(n) < 1 - np.exp(-z * age))
    a, b = beta_par(m, SD)
    p = rng.beta(a, b, n)
    return age, dead, aband, p


def one_send(rng, dead, aband, p, v):
    n = len(dead)
    reader = (~dead) & (~aband)
    soft = (~dead) & (rng.random(n) < np.where(aband, v, SOFT_ACTIVE))
    delivered = (~dead) & (~soft)
    opened = delivered & reader & (rng.random(n) < p)
    o = opened.sum()
    return {"sent": n, "hard": int(dead.sum()), "soft": int(soft.sum()), "delivered": int(delivered.sum()),
            "readers_delivered": int((delivered & reader).sum()), "abandoned_delivered": int((delivered & aband).sum()), "opens": int(o),
            "r1": o / n, "r2": o / (n - dead.sum()), "r3": o / delivered.sum(), "r4": o / (delivered & reader).sum()}


def pair_agree(vals, truth):
    ok = [np.sign(vals[i] - vals[j]) == np.sign(truth[i] - truth[j]) for i, j in combinations(range(len(vals)), 2)]
    return float(np.mean(ok))


def shops_run(rng, R, h, z, v, ms, shuffle=False):
    rows = []
    for rep in range(R):
        mm = rng.permutation(ms) if shuffle else ms
        for s, (Lm, m) in enumerate(zip(L, mm)):
            age, dead, aband, p = make_list(rng, Lm, m, h, z)
            o = one_send(rng, dead, aband, p, v)
            o.update({"rep": rep, "shop": SHOPS[s], "m": m})
            rows.append(o)
    return pd.DataFrame(rows)


# (1) 6店
df = shops_run(rng, R_MAIN, H, Z, V, M_BASE)
tab = df.groupby("shop", sort=False).agg(sent=("sent", "mean"), hard=("hard", "mean"), soft=("soft", "mean"), delivered=("delivered", "mean"),
                                         abandoned_delivered=("abandoned_delivered", "mean"),
                                         r1=("r1", "mean"), r2=("r2", "mean"), r3=("r3", "mean"), r4=("r4", "mean")).reset_index()
tab["list_months_max"] = L
tab["true_reader_open"] = M_BASE
tab["hard_share"] = tab.hard / tab.sent
tab["soft_share"] = tab.soft / tab.sent
tab["abandoned_share_of_delivered"] = tab.abandoned_delivered / tab.delivered
tab["r1_over_r3"] = tab.r1 / tab.r3
tab["r3_over_r4"] = tab.r3 / tab.r4
tab = tab.round(4)
tab.to_csv(RES / "shops.csv", index=False)

# 回ごとの、店の上下の当たり（15組）と1位
agree, top = {k: [] for k in ["r1", "r2", "r3"]}, {k: [] for k in ["r1", "r2", "r3", "r4"]}
for rep, g in df.groupby("rep"):
    for k in ["r1", "r2", "r3"]:
        agree[k].append(pair_agree(g[k].values, M_BASE))
    for k in top:
        top[k].append(g.shop.values[g[k].values.argmax()])
agree_main = {k: r(np.mean(v)) for k, v in agree.items()}
top_main = {k: pd.Series(v).value_counts(normalize=True).round(4).to_dict() for k, v in top.items()}
# 平均の値での並び（店の数字そのもの）
mean_order = {k: list(tab.sort_values(k, ascending=False).shop) for k in ["r1", "r2", "r3", "r4"]}

# 1回分の例を data に
ex_rng = np.random.default_rng(SEED + 1)
ex_rows = []
for s, (Lm, m) in enumerate(zip(L, M_BASE)):
    age, dead, aband, p = make_list(ex_rng, Lm, m, H, Z)
    n = len(dead)
    soft = (~dead) & (ex_rng.random(n) < np.where(aband, V, SOFT_ACTIVE))
    delivered = (~dead) & (~soft)
    opened = delivered & (~aband) & (ex_rng.random(n) < p)
    status = np.where(dead, "hard", np.where(soft, "soft", "delivered"))
    ex_rows.append(pd.DataFrame({"shop": SHOPS[s], "address_id": np.arange(n), "months_since_signup": np.round(age, 1),
                                 "status": status, "abandoned": aband.astype(int), "opened": opened.astype(int)}))
pd.concat(ex_rows, ignore_index=True).to_csv(DATA / "one_send_all_shops.csv", index=False)

# (2) 月ごとの例（C店）
mr = np.random.default_rng(SEED + 2)
age, dead, aband, p = make_list(mr, 24, 0.30, H, Z)
a_, b_ = beta_par(0.30, SD)
months = []
for mo in range(1, 13):
    if mo > 1:
        # 1か月たつ
        alive = ~dead
        newdead = alive & (mr.random(len(dead)) < 1 - np.exp(-H))
        newab = alive & ~newdead & ~aband & (mr.random(len(dead)) < 1 - np.exp(-Z))
        dead = dead | newdead
        aband = aband | newab
        age = age + 1
        # 新しく登録した100人
        age = np.concatenate([age, np.zeros(100)])
        dead = np.concatenate([dead, np.zeros(100, bool)])
        aband = np.concatenate([aband, np.zeros(100, bool)])
        p = np.concatenate([p, mr.beta(a_, b_, 100)])
    o = one_send(mr, dead, aband, p, V)
    o["month"] = mo
    months.append(o)
    if mo >= 7:   # 7か月目の配信から、戻ったアドレスをリストから消す
        keep = ~dead
        age, dead, aband, p = age[keep], dead[keep], aband[keep], p[keep]
mon = pd.DataFrame(months)[["month", "sent", "hard", "soft", "delivered", "readers_delivered", "opens", "r1", "r2", "r3", "r4"]].round(4)
mon.to_csv(RES / "monthly_shopC.csv", index=False)

# (3) 確かめ
grid = []
for h in [0.005, 0.01, 0.02]:
    for z in [0.0, 0.015, 0.03]:
        for v in [0.02, 0.2]:
            for step in [0.01, 0.02]:
              for order in ["古いほど高い", "でたらめ"]:
                ms = [0.31 + step * (i - 2.5) for i in range(6)]
                d = shops_run(rng, R_GRID, h, z, v, ms, shuffle=(order == "でたらめ"))
                ag = {k: [] for k in ["r1", "r2", "r3"]}
                for rep, g in d.groupby("rep"):
                    for k in ag:
                        ag[k].append(pair_agree(g[k].values, g["m"].values))
                mm = d.groupby("shop", sort=False)[["r1", "r2", "r3", "r4"]].mean()
                grid.append({"h": h, "z": z, "v": v, "step": step, "order": order,
                             "agree_r1": r(np.mean(ag["r1"])), "agree_r2": r(np.mean(ag["r2"])), "agree_r3": r(np.mean(ag["r3"])),
                             "F_r1_over_r3": r(mm.loc["F店", "r1"] / mm.loc["F店", "r3"]), "F_r3_over_r4": r(mm.loc["F店", "r3"] / mm.loc["F店", "r4"]),
                             "A_r1_over_r3": r(mm.loc["A店", "r1"] / mm.loc["A店", "r3"]),
                             # 店の差は、開く確率を古いリストほど高く置いたときだけ意味がある（でたらめの割り当てでは空）
                             "F_minus_A_r1": r(mm.loc["F店", "r1"] - mm.loc["A店", "r1"]) if order == "古いほど高い" else None,
                             "F_minus_A_r3": r(mm.loc["F店", "r3"] - mm.loc["A店", "r3"]) if order == "古いほど高い" else None,
                             "F_minus_A_r4": r(mm.loc["F店", "r4"] - mm.loc["A店", "r4"]) if order == "古いほど高い" else None})
grid = pd.DataFrame(grid)
grid.to_csv(RES / "grid.csv", index=False)

# 式：①÷③ ＝ 届いた数÷送った数（作りどおり）。期待値の式で確かめる
def expected_r1_over_r3(Lm, h, z, v):
    ages = np.linspace(0, Lm, 20001)
    pd_ = 1 - np.exp(-h * ages)
    pa = np.exp(-h * ages) * (1 - np.exp(-z * ages))
    pr = np.exp(-h * ages) * np.exp(-z * ages)
    return float(np.mean(pr * (1 - SOFT_ACTIVE) + pa * (1 - v)))


formula = [r(expected_r1_over_r3(Lm, H, Z, V)) for Lm in L]

res = {
    "settings": {"shops": SHOPS, "list_months_max": L, "true_reader_open": M_BASE, "addresses": NADDR, "hard_per_month": H,
                 "abandon_per_month": Z, "soft_active": SOFT_ACTIVE, "soft_abandoned": V, "reader_sd": SD,
                 "reps_main": R_MAIN, "reps_grid": R_GRID, "seed": SEED},
    "shops": tab.to_dict(orient="records"),
    "formula_r1_over_r3": formula,
    "formula_max_gap": r(np.max(np.abs(np.array(formula) - tab.r1_over_r3.values))),
    "pair_agree_main": agree_main,
    "top_share_main": top_main,
    "mean_order": mean_order,
    "monthly": {"r1_m6": r(mon.r1[5]), "r1_m7": r(mon.r1[6]), "r1_m8": r(mon.r1[7]), "r3_m6": r(mon.r3[5]), "r3_m7": r(mon.r3[6]), "r3_m8": r(mon.r3[7]),
                "r1_m1": r(mon.r1[0]), "r1_m12": r(mon.r1[11]), "r3_m1": r(mon.r3[0]), "r3_m12": r(mon.r3[11]),
                "r4_m1": r(mon.r4[0]), "r4_m12": r(mon.r4[11]), "hard_m6": int(mon.hard[5]), "hard_m7": int(mon.hard[6]), "hard_m8": int(mon.hard[7]),
                "sent_m7": int(mon.sent[6]), "sent_m8": int(mon.sent[7]),
                "r1_m8_minus_m7": r(mon.r1[7] - mon.r1[6]), "r3_m8_minus_m7": r(mon.r3[7] - mon.r3[6]), "r4_m8_minus_m7": r(mon.r4[7] - mon.r4[6])},
    "robust": {
        "n": len(grid),
        "agree_r1_min": r(grid.agree_r1.min()), "agree_r1_max": r(grid.agree_r1.max()),
        "agree_r2_min": r(grid.agree_r2.min()), "agree_r2_max": r(grid.agree_r2.max()),
        "agree_r3_min": r(grid.agree_r3.min()), "agree_r3_max": r(grid.agree_r3.max()),
        "share_r3_ge_r1": r(np.mean(grid.agree_r3 >= grid.agree_r1) * 100, 2),
        "F_r1_over_r3_min": r(grid.F_r1_over_r3.min()), "F_r1_over_r3_max": r(grid.F_r1_over_r3.max()),
        "F_r3_over_r4_min": r(grid.F_r3_over_r4.min()), "F_r3_over_r4_max": r(grid.F_r3_over_r4.max()),
        "z0_F_r3_over_r4_max": r(grid[grid.z == 0].F_r3_over_r4.max()), "z0_F_r3_over_r4_min": r(grid[grid.z == 0].F_r3_over_r4.min()),
        "FA_r1_negative_count_old_high": int((grid[grid.order == "古いほど高い"].F_minus_A_r1 < 0).sum()), "FA_r3_negative_count_old_high": int((grid[grid.order == "古いほど高い"].F_minus_A_r3 < 0).sum()),
        "by_order": [{"order": o, "agree_r1_min": r(g.agree_r1.min()), "agree_r1_max": r(g.agree_r1.max()), "agree_r1_median": r(g.agree_r1.median()),
                      "agree_r2_min": r(g.agree_r2.min()), "agree_r2_max": r(g.agree_r2.max()), "agree_r2_median": r(g.agree_r2.median()),
                      "agree_r3_min": r(g.agree_r3.min()), "agree_r3_max": r(g.agree_r3.max()), "agree_r3_median": r(g.agree_r3.median()),
                      "share_r3_gt_r1": r(np.mean(g.agree_r3 > g.agree_r1) * 100, 2)} for o, g in grid.groupby("order", sort=False)],
        "by_order_z0": [{"order": o, "agree_r3_min": r(g.agree_r3.min()), "agree_r3_max": r(g.agree_r3.max()), "agree_r1_min": r(g.agree_r1.min()), "agree_r1_max": r(g.agree_r1.max())}
                        for o, g in grid[grid.z == 0].groupby("order", sort=False)],
        "by_h": [{"h": h, "agree_r1_min": r(g.agree_r1.min()), "agree_r1_max": r(g.agree_r1.max()), "agree_r3_min": r(g.agree_r3.min()),
                  "agree_r3_max": r(g.agree_r3.max())} for h, g in grid[grid.order == "古いほど高い"].groupby("h")],
        "by_step": [{"step": st, "agree_r1_min": r(g.agree_r1.min()), "agree_r1_max": r(g.agree_r1.max()), "agree_r3_min": r(g.agree_r3.min()),
                     "agree_r3_max": r(g.agree_r3.max())} for st, g in grid[grid.order == "古いほど高い"].groupby("step")],
    },
}

# 図1：店ごとの4つの開封率
fig, ax = plt.subplots(figsize=(8.6, 4.6))
x = np.arange(6)
w = 0.2
labs = ["①送った数で割る", "②ハードバウンスを除く", "③届いた数で割る", "④届いた読む人で割る（本当）"]
cols = [GRAY, LIGHT, BLUE, ORANGE]
for i, k in enumerate(["r1", "r2", "r3", "r4"]):
    ax.bar(x + (i - 1.5) * w, tab[k] * 100, w, color=cols[i], label=labs[i])
for i in range(6):
    ax.text(x[i] - 1.5 * w, tab.r1[i] * 100 + 0.4, f"{tab.r1[i]*100:.2f}", ha="center", fontsize=7.5, rotation=90, va="bottom")
    ax.text(x[i] + 0.5 * w, tab.r3[i] * 100 + 0.4, f"{tab.r3[i]*100:.2f}", ha="center", fontsize=7.5, rotation=90, va="bottom")
ax.set_xticks(x)
ax.set_xticklabels([f"{s}\n（登録0〜{l}か月）" for s, l in zip(SHOPS, L)], fontsize=9)
ax.set_ylabel("開封率（%、200回の平均）")
ax.set_ylim(0, 45)
ax.set_title("分母を変えた開封率（数字は①と③）")
ax.legend(fontsize=8.5, ncol=2, frameon=False, loc="upper left")
save(fig, "a1198_shops.png", SRC)

# 図2：月ごと（C店）
fig, ax = plt.subplots(figsize=(7.4, 4.4))
ax.plot(mon.month, mon.r1 * 100, "o-", color=GRAY, label="①送った数で割る")
ax.plot(mon.month, mon.r3 * 100, "o-", color=BLUE, label="③届いた数で割る")
ax.plot(mon.month, mon.r4 * 100, "s--", color=ORANGE, label="④届いた読む人で割る（本当）")
ax.axvline(7.5, color=GRAY, lw=0.8, ls=":")
ax.text(7.6, 15.5, "7か月目の配信のあとから、\n戻ったアドレスを消す", fontsize=9, color=INK, va="bottom")
ax.set_xlabel("月")
ax.set_ylabel("開封率（%）")
ax.set_ylim(0, 35)
ax.set_xticks(range(1, 13))
ax.set_title("C店の12か月（1回ずつの配信）")
ax.legend(fontsize=9, frameon=False, loc="lower left")
save(fig, "a1198_monthly.png", SRC)

# 図3：確かめ（店の上下の当たり）
fig, ax = plt.subplots(figsize=(7.4, 4.4))
gs = pd.concat([grid[grid.order == o].sort_values("agree_r1") for o in ["古いほど高い", "でたらめ"]]).reset_index(drop=True)
ax.plot(gs.index + 1, gs.agree_r1 * 100, "o", color=GRAY, ms=4, label="①送った数で割る")
ax.plot(gs.index + 1, gs.agree_r3 * 100, "o", color=BLUE, ms=4, label="③届いた数で割る")
ax.axvline(36.5, color=GRAY, lw=0.8, ls=":")
ax.text(18.5, 101.5, "開く確率は古いリストほど高い", ha="center", va="bottom", fontsize=9)
ax.text(54.5, 101.5, "開く確率を店にでたらめに割り当て", ha="center", va="bottom", fontsize=9)
ax.set_xlabel("72通りの置き方（それぞれの中で①の当たりの低い順）")
ax.set_ylabel("店2つずつの上下が本当と\n同じだった割合（15組、%）")
ax.set_ylim(0, 100)
ax.set_title("置き方を変えた72通り（各100回）", pad=26)
ax.legend(fontsize=9, frameon=False, loc="lower right")
save(fig, "a1198_grid.png", SRC)

with open(RES / "a1198_main.json", "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print(tab.to_string())
print(agree_main, top_main, mean_order)
print(mon.to_string())
print(json.dumps(res["robust"], ensure_ascii=False))
print("formula", formula, res["formula_max_gap"], "sec", round(time.time() - T0, 1))
