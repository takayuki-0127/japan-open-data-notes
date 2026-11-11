"""送る時刻の決め方3つで、「古い数字のまま送った週」と「届く時刻」を比べる"""
import json, numpy as np, pandas as pd, matplotlib.pyplot as plt
from common import DATA, RES, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN
rt = pd.read_csv(DATA / "ready_time.csv")
def simulate(ready):
    """ready：各週の集計が終わる時刻（時）。戻り値：規則ごとの (古い数字で送ったか, 届いた時刻)"""
    out = {}
    out["A：毎週7:00に送る"] = (ready > 7.0, np.full(len(ready), 7.0))
    out["B：毎週9:00に送る"] = (ready > 9.0, np.full(len(ready), 9.0))
    # C：7:00 に確認し、そろっていなければ30分おきに確認し直す。12:00 までにそろわなければ「遅れ」の知らせだけ送る
    t = np.where(ready <= 7.0, 7.0, 7.0 + np.ceil((ready - 7.0) / 0.5) * 0.5)
    gave_up = t > 12.0
    out["C：7:00に確認、そろうまで30分おき"] = (np.zeros(len(ready), bool), np.where(gave_up, 12.0, t))
    out["C：7:00に確認、そろうまで30分おき"] += (gave_up,)
    return out
one = simulate(rt["ready_hour"].to_numpy())
res = {"weeks": len(rt), "late_weeks": int(rt["late"].sum()), "one_year": {}}
for k, v in one.items():
    res["one_year"][k] = {"stale_weeks": int(v[0].sum()), "median_send": float(np.median(v[1])), "mean_send": float(np.mean(v[1])),
                          "gave_up": int(v[2].sum()) if len(v) > 2 else 0}
# 前提を変えて：遅れる週の割合 5%・10%・20% で、それぞれ 2,000 年ぶん
rng = np.random.default_rng(2800)
sens = []
for p in [0.05, 0.10, 0.20]:
    ready = 6.5 + rng.normal(0, 0.3, (2000, 52)); late = rng.random((2000, 52)) < p
    ready = ready + late * rng.uniform(1, 5, (2000, 52))
    sim = simulate(ready.ravel())
    for k, v in sim.items():
        sens.append({"late_rate": p, "rule": k, "stale_share": float(v[0].mean()), "median_send": float(np.median(v[1])),
                     "mean_send": float(np.mean(v[1])), "p90_send": float(np.quantile(v[1], 0.9)),
                     "gave_up_share": float(v[2].mean()) if len(v) > 2 else 0.0})
pd.DataFrame(sens).to_csv(RES / "send_rules_sensitivity.csv", index=False)
res["sensitivity"] = sens
json.dump(res, open(RES / "send_rules.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(res["one_year"], ensure_ascii=False, indent=1))
# 図2：1年の52週
fig, ax = plt.subplots(figsize=(10, 4))
x = np.arange(1, 53); r = rt["ready_hour"]
ax.scatter(x, r, s=18, color=np.where(r > 7, ORANGE, BLUE), zorder=3)
ax.hlines(7, 0, 52.5, color=INK, lw=1); ax.text(53, 7, "7:00 に送る", va="center", fontsize=9)
ax.hlines(9, 0, 52.5, color=GRAY, lw=1, ls="--"); ax.text(53, 9, "9:00 に送る", va="center", fontsize=9, color=GRAY)
ax.set_xlim(0, 58); ax.set_ylim(5.5, 12.2); ax.invert_yaxis()
ax.set_xlabel("週（2025年）"); ax.set_ylabel("集計が終わった時刻（時）")
a = res["one_year"]
ax.set_title(f"7:00 に決め打ちで送ると、52週中 {a['A：毎週7:00に送る']['stale_weeks']}週は先週の数字がそろう前に送っていた（橙の点）")
save(fig, "a280_ready_times.png")
# 図3：前提ごとの比べ
s = pd.DataFrame(sens); rules = list(one)
fig, axs = plt.subplots(1, 2, figsize=(11, 3.9))
w = 0.26
for i, rule in enumerate(rules):
    d = s[s.rule == rule]; xx = np.arange(3) + (i - 1) * w
    c = [ORANGE, GRAY, BLUE][i]
    axs[0].bar(xx, d.stale_share * 100, w, color=c, label=rule)
    axs[1].bar(xx, d.mean_send - 7, w, color=c)
for ax in axs: ax.set_xticks(range(3), ["遅れる週 5%", "10%", "20%"])
axs[0].set_ylabel("古い数字で送った週の割合（%）"); axs[0].legend(frameon=False, fontsize=8.5, loc="upper left")
axs[1].text(-0.26, 0.04, "A は 7:00 ちょうど（0）", fontsize=8, color=ORANGE, rotation=90, va="bottom")
axs[1].set_ylabel("届く時刻の平均（7:00 から何時間あと）")
axs[0].set_title("古い数字を送った割合"); axs[1].set_title("届くまでの遅さ")
fig.suptitle("「そろったか確かめてから送る」は、古い数字を0にし、平均の遅れは数十分ですむ（架空の前提、各2,000年）", y=1.03, fontsize=11.5)
save(fig, "a280_rules_compare.png")
