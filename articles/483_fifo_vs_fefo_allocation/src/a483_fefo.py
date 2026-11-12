"""483 在庫を「入った順」と「期限の近い順」で引き当てると、欠品と廃棄は何件変わるのか（架空の30品目・2年分）"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, save, BLUE, ORANGE, GRAY, INK, GREEN

SRC = "架空の入荷・出荷（作成者が乱数で作成、seed 483）"
DAYS, WARM = 760, 30          # 30日の助走のあと730日を数える
LEAD, LIFE, MINLEFT, REVIEW, CASE = 2, 7, 1, 3, 12  # 入荷まで2日、残り期限の中心7日、出荷は残り1日以上、3日ごとに発注、12個単位
COST, PRICE = 200, 300        # 1個の仕入れ値・売値（円）


def products(rng, n=30):
    mu = np.round(np.exp(rng.uniform(np.log(5), np.log(100), n)), 1)   # 1日の平均需要 5〜100個
    return pd.DataFrame({"item": np.arange(n), "mean_demand": mu})


def run(mu, var, rule, seed, cover=1.6):
    """var：入荷するロットの残り期限のばらつき（±日）。rule：FIFO（入った順）・FEFO（期限の近い順）・LIFO（新しい順）"""
    r = np.random.default_rng(seed)
    wk = np.array([0.85, 0.85, 0.9, 0.95, 1.1, 1.25, 1.1])[np.arange(DAYS) % 7]
    dem = r.poisson(r.gamma(4.0, mu * wk / 4.0))   # 曜日の波＋日ごとの揺れ
    life = LIFE + r.integers(-var, var + 1, DAYS) if var > 0 else np.full(DAYS, LIFE)
    lots = []          # [arrive_day, expire_day, qty]
    pipe = {}          # 入荷予定 day -> qty
    H = LEAD + REVIEW
    S = int(np.ceil(mu * H + cover * np.sqrt(mu * H + (mu ** 2) * H / 4.0)))   # ここまで補充する水準
    waste = short = short_days = sold = 0; wl = []
    for t in range(DAYS):
        if t in pipe:
            lots.append([t, t + int(life[t]), pipe.pop(t)])
        # 期限切れ（残り期限が MINLEFT 未満）は廃棄
        keep = []
        for L in lots:
            if L[1] - t < MINLEFT:
                if t >= WARM: waste += L[2]
            else: keep.append(L)
        lots = keep
        if rule == "FIFO": lots.sort(key=lambda L: (L[0], L[1]))
        elif rule == "FEFO": lots.sort(key=lambda L: (L[1], L[0]))
        else: lots.sort(key=lambda L: (-L[0], -L[1]))
        need = dem[t]
        for L in lots:
            if need == 0: break
            k = min(need, L[2]); L[2] -= k; need -= k
            if t >= WARM: sold += k
        lots = [L for L in lots if L[2] > 0]
        if t >= WARM and need > 0: short += need; short_days += 1
        pos = sum(L[2] for L in lots) + sum(pipe.values())
        q = S - pos
        if t % REVIEW == 0 and q > 0:
            q = int(np.ceil(q / CASE) * CASE)
            pipe[t + LEAD] = pipe.get(t + LEAD, 0) + q
    return {"waste": waste, "short": short, "short_days": short_days, "sold": sold, "demand": int(dem[WARM:].sum())}


rng = np.random.default_rng(483)
P = products(rng); P.to_csv(DATA / "fictional_items.csv", index=False)
rows = []
for var in [0, 1, 2, 3, 4, 6]:
    for rule in ["FIFO", "FEFO", "LIFO"]:
        for _, p in P.iterrows():
            for rep in range(3):
                o = run(p.mean_demand, var, rule, seed=483_000 + int(p["item"]) * 10 + rep)
                rows.append({"var": var, "rule": rule, "item": int(p["item"]), "mean_demand": p.mean_demand, "rep": rep, **o})
R = pd.DataFrame(rows); R.to_csv(RES / "runs.csv", index=False)
agg = R.groupby(["var", "rule"])[["waste", "short", "short_days", "sold", "demand"]].sum().reset_index()
agg["waste_per_1000"] = agg.waste / agg.demand * 1000
agg["short_per_1000"] = agg.short / agg.demand * 1000
agg["waste_yen_per_item_year"] = agg.waste * COST / (30 * 3 * 2)
agg["lost_yen_per_item_year"] = agg.short * PRICE / (30 * 3 * 2)
agg.to_csv(RES / "by_variability.csv", index=False)
# 回転の速さ別（var=3）
R3 = R[R["var"] == 3].copy(); R3["speed"] = pd.cut(R3.mean_demand, [0, 15, 40, 101], labels=["遅い（〜15個/日）", "中（15〜40）", "速い（40〜）"])
sp = R3.groupby(["speed", "rule"], observed=True)[["waste", "short", "demand"]].sum().reset_index()
sp["waste_per_1000"] = sp.waste / sp.demand * 1000; sp["short_per_1000"] = sp.short / sp.demand * 1000
sp.to_csv(RES / "by_speed_var3.csv", index=False)
# 安全在庫の厚さ（cover）を変えたときの、廃棄と欠品の入れ替わり（var=3）
tr = []
for cover in [0.8, 1.2, 1.6, 2.0, 2.5, 3.0]:
    for rule in ["FIFO", "FEFO"]:
        tot = {"waste": 0, "short": 0, "demand": 0}
        for _, p in P.iterrows():
            o = run(p.mean_demand, 3, rule, seed=483_000 + int(p["item"]) * 10, cover=cover)
            for k in tot: tot[k] += o[k]
        tr.append({"cover": cover, "rule": rule, "waste_per_1000": tot["waste"] / tot["demand"] * 1000,
                   "short_per_1000": tot["short"] / tot["demand"] * 1000})
tr = pd.DataFrame(tr); tr.to_csv(RES / "tradeoff_cover.csv", index=False)

g = lambda v, r, c: float(agg[(agg["var"] == v) & (agg.rule == r)][c].iloc[0])
res = {"items": 30, "reps": 3, "days_counted": DAYS - WARM,
       "by_var": agg.round(3).to_dict("records"),
       "var3": {r: {"waste": int(g(3, r, "waste")), "short": int(g(3, r, "short")), "short_days": int(g(3, r, "short_days")),
                    "waste_per_1000": g(3, r, "waste_per_1000"), "short_per_1000": g(3, r, "short_per_1000")} for r in ["FIFO", "FEFO", "LIFO"]},
       "var0_same": bool(g(0, "FIFO", "waste") == g(0, "FEFO", "waste") and g(0, "FIFO", "short") == g(0, "FEFO", "short")),
       "by_speed_var3": sp.round(3).astype({"speed": str}).to_dict("records"),
       "tradeoff": tr.round(3).to_dict("records")}
json.dump(res, open(RES / "a483_main.json", "w"), ensure_ascii=False, indent=1, default=float)

lab = {"FIFO": "入った順", "FEFO": "期限の近い順", "LIFO": "新しい順（参考）"}
col = {"FIFO": BLUE, "FEFO": ORANGE, "LIFO": GRAY}
# 図1：残り期限のばらつきと廃棄・欠品
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
for rule in ["FIFO", "FEFO", "LIFO"]:
    a = agg[agg.rule == rule]
    axs[0].plot(a["var"], a.waste_per_1000, "o-", color=col[rule], lw=2, label=lab[rule])
    axs[1].plot(a["var"], a.short_per_1000, "o-", color=col[rule], lw=2, label=lab[rule])
axs[0].set_title("廃棄（需要1,000個あたり）", loc="left", fontsize=11); axs[1].set_title("欠品（需要1,000個あたり）", loc="left", fontsize=11)
for ax in axs: ax.set_xlabel("入荷するロットの残り期限のばらつき（±日、中心7日）"); ax.grid(axis="y", alpha=.3); ax.set_ylim(0, None)
axs[0].legend(frameon=False, fontsize=9)
save(fig, "a483_by_variability.png", SRC)
# 図2：回転の速さ別（var=3）
fig, axs = plt.subplots(1, 2, figsize=(11, 4.2))
cats = list(sp.speed.cat.categories) if hasattr(sp.speed, "cat") else sorted(sp.speed.unique())
xs = np.arange(len(cats))
for j, rule in enumerate(["FIFO", "FEFO", "LIFO"]):
    a = sp[sp.rule == rule].set_index("speed").reindex(cats)
    axs[0].bar(xs + (j - 1) * .27, a.waste_per_1000, .27, color=col[rule], label=lab[rule])
    axs[1].bar(xs + (j - 1) * .27, a.short_per_1000, .27, color=col[rule], label=lab[rule])
for ax, t in zip(axs, ["廃棄（需要1,000個あたり）", "欠品（需要1,000個あたり）"]):
    ax.set_xticks(xs); ax.set_xticklabels(cats, fontsize=9); ax.set_title(t, loc="left", fontsize=11)
axs[0].legend(frameon=False, fontsize=8)
fig.suptitle("売れる速さ別（残り期限のばらつき±3日）", x=0.01, ha="left", fontsize=12)
save(fig, "a483_by_speed.png", SRC)
# 図3：安全在庫の厚さを変えたときの廃棄と欠品
fig, ax = plt.subplots(figsize=(7.5, 5))
for rule in ["FIFO", "FEFO"]:
    a = tr[tr.rule == rule]
    ax.plot(a.short_per_1000, a.waste_per_1000, "o-", color=col[rule], lw=2, label=lab[rule])
    for _, r in a.iterrows(): ax.annotate(f"{r.cover:g}", (r.short_per_1000, r.waste_per_1000), textcoords="offset points", xytext=(5, 4), fontsize=8, color=col[rule])
ax.set_xlabel("欠品（需要1,000個あたり）"); ax.set_ylabel("廃棄（需要1,000個あたり）")
ax.set_title("在庫を厚くするほど欠品は減り廃棄は増える（数字は安全在庫の厚さ）", loc="left", fontsize=11)
ax.legend(frameon=False); ax.grid(alpha=.3)
save(fig, "a483_tradeoff.png", SRC)
print(agg.round(2).to_string()); print(sp.round(2).to_string()); print(tr.round(2).to_string())
