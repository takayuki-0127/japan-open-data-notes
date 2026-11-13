"""614 平均の問い合わせ件数から窓口の人数を決めると、待ち時間はどれだけ長くなるのか

架空の問い合わせ窓口：9時〜18時（30分ごと18区間）、1日720件、1件の対応は平均6分（指数分布）。件数は午前と昼過ぎに山がある。
人数の決め方を3つ比べる。
  N1 1日の平均の仕事量で全時間同じ人数（720件×6分÷9時間＝8人）
  N2 30分ごとの仕事量（件数×6分÷30分）を切り上げた人数
  N3 30分ごとにアーラン C の式で、20秒以内に出られる割合が80%以上になる最小の人数
1日の電話の流れ（到着はポアソン）を300日分シミュレーションし、待ち時間・20秒以内の応答率・延べ人時間を数える。
途中で切る人（放棄）は入れていない。seed 614。
"""
import json
import heapq
import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, save, BLUE, ORANGE, GRAY, LIGHT, GREEN

SRC = "出典：シミュレーション（作成者が乱数で作成、seed 614）"
rng = np.random.default_rng(614)
AHT, SL_T, DAYS = 6.0, 20 / 60, 300
shape = np.array([0.6, 1.0, 1.5, 1.7, 1.6, 1.3, 1.0, 0.8, 0.9, 1.3, 1.5, 1.4, 1.1, 0.9, 0.8, 0.7, 0.6, 0.5])
lam = 720 * shape / shape.sum()           # 区間ごとの平均件数
traffic = lam * AHT / 30                  # 区間ごとの仕事量（アーラン）


def erlang_c(a, c):
    if c <= a:
        return 1.0
    s = sum(a ** k / math.factorial(k) for k in range(c))
    top = a ** c / math.factorial(c) * c / (c - a)
    return top / (s + top)


def service_level(a, c, t):
    if c <= a:
        return 0.0
    return 1 - erlang_c(a, c) * math.exp(-(c - a) * t / AHT)


N1 = np.full(18, int(math.ceil(720 * AHT / 540)))
N2 = np.ceil(traffic).astype(int)
N3 = np.array([next(c for c in range(int(a) + 1, 60) if service_level(a, c, SL_T) >= 0.8) for a in traffic])
plans = {"N1": N1, "N2": N2, "N3": N3}


def simulate(staff, seed):
    rs = np.random.default_rng(seed)
    waits, ivs = [], []
    servers = [0.0] * int(staff[0])
    heapq.heapify(servers)
    for i in range(18):
        t0 = i * 30.0
        # 人数を合わせる：増えるときは区間の始まりから空く人を足し、減るときは早く空く人から抜ける
        need = int(staff[i])
        servers = sorted(servers)
        if need > len(servers):
            servers += [t0] * (need - len(servers))
        elif need < len(servers):
            servers = servers[len(servers) - need:]
        heapq.heapify(servers)
        n = rs.poisson(lam[i])
        arr = np.sort(rs.uniform(t0, t0 + 30, n)); svc = rs.exponential(AHT, n)
        for a, s in zip(arr, svc):
            free = heapq.heappop(servers)
            start = max(a, free)
            waits.append(start - a); ivs.append(i)
            heapq.heappush(servers, start + s)
    return np.array(waits), np.array(ivs)


rows, iv_rows = [], []
for k, st in plans.items():
    W, I = [], []
    for d in range(DAYS):
        w, iv = simulate(st, 614_000 + d)
        W.append(w); I.append(iv)
    W = np.concatenate(W); I = np.concatenate(I)
    rows.append({"plan": k, "staff_hours": float(st.sum() * 0.5), "mean_wait_sec": round(float(W.mean() * 60), 1),
                 "sl20_pct": round(float((W <= SL_T).mean() * 100), 1), "p90_wait_sec": round(float(np.quantile(W, 0.9) * 60), 1),
                 "wait_over_5min_pct": round(float((W > 5).mean() * 100), 2)})
    for i in range(18):
        wi = W[I == i]
        iv_rows.append({"plan": k, "interval": i, "staff": int(st[i]), "traffic": round(float(traffic[i]), 2),
                        "mean_wait_sec": round(float(wi.mean() * 60), 1), "sl20_pct": round(float((wi <= SL_T).mean() * 100), 1),
                        "erlang_sl20_pct": round(100 * service_level(traffic[i], int(st[i]), SL_T), 1)})
sm = pd.DataFrame(rows); ivd = pd.DataFrame(iv_rows)
sm.to_csv(RES / "summary.csv", index=False); ivd.to_csv(RES / "by_interval.csv", index=False)
out = {"calls_per_day": 720, "aht_min": AHT, "days": DAYS, "traffic_peak": round(float(traffic.max()), 2), "traffic_mean": round(float(traffic.mean()), 2),
       "plans": {k: v.tolist() for k, v in plans.items()}, "summary": rows,
       "peak_interval_wait_sec": {k: float(ivd[(ivd.plan == k)].mean_wait_sec.max()) for k in plans}}
json.dump(out, open(RES / "a614_main.json", "w"), ensure_ascii=False, indent=1)

lab = {"N1": "1日の平均で同じ人数", "N2": "30分ごとの仕事量を切り上げ", "N3": "30分ごとにアーラン C（80%を20秒以内）"}
col = {"N1": ORANGE, "N2": BLUE, "N3": GREEN}
tl = [f"{9 + i // 2}:{'00' if i % 2 == 0 else '30'}" for i in range(18)]
# 図1：人数と仕事量
fig, ax = plt.subplots(figsize=(9, 3.8))
ax.bar(range(18), traffic, color=LIGHT, label="仕事量（同時に対応が要る人数の平均）")
for k in plans:
    ax.step(range(18), plans[k], where="mid", color=col[k], lw=2, label=lab[k])
ax.set_xticks(range(0, 18, 2)); ax.set_xticklabels(tl[::2]); ax.set_ylabel("人数")
ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.2)); ax.set_ylim(0, 18)
ax.set_title("30分ごとの仕事量と、3つの決め方の人数", pad=48)
save(fig, "a614_staffing_plans.png", SRC)
# 図2：区間ごとの平均の待ち時間
fig, ax = plt.subplots(figsize=(9, 3.8))
for k in plans:
    s = ivd[ivd.plan == k]
    ax.plot(range(18), s.mean_wait_sec / 60, marker="o", ms=3, color=col[k], label=lab[k])
ax.set_yscale("log"); ax.set_yticks([0.1, 0.5, 1, 5, 10, 60]); ax.set_yticklabels(["0.1", "0.5", "1", "5", "10", "60"])
ax.set_xticks(range(0, 18, 2)); ax.set_xticklabels(tl[::2])
ax.set_ylabel("平均の待ち時間（分、対数の目盛り）"); ax.legend(frameon=False, fontsize=8, loc="lower right")
ax.set_title("30分ごとの平均の待ち時間（300日の平均）")
save(fig, "a614_wait_by_interval.png", SRC)
# 図3：全体の応答率と人時間
fig, axs = plt.subplots(1, 2, figsize=(11, 3.6), gridspec_kw={"wspace": 0.45})
ks = list(plans)
short = {"N1": "1日の平均で\n8人", "N2": "仕事量を\n切り上げ", "N3": "アーラン C\n（80%を20秒）"}
axs[0].bar([short[k] for k in ks], [r["sl20_pct"] for r in rows], color=[col[k] for k in ks])
for i, r in enumerate(rows):
    axs[0].text(i, r["sl20_pct"], f"{r['sl20_pct']:.0f}%", ha="center", va="bottom")
axs[0].set_title("20秒以内に出られた割合（1日全体）"); axs[0].set_ylim(0, 105); axs[0].tick_params(axis="x", labelsize=9)
axs[1].bar([short[k] for k in ks], [r["staff_hours"] for r in rows], color=[col[k] for k in ks])
for i, r in enumerate(rows):
    axs[1].text(i, r["staff_hours"], f"{r['staff_hours']:.0f}人時", ha="center", va="bottom")
axs[1].set_title("1日の延べ人時間"); axs[1].tick_params(axis="x", labelsize=9); axs[1].set_ylim(0, max(r["staff_hours"] for r in rows) * 1.2)
save(fig, "a614_service_and_hours.png", SRC, y=-0.06)
print(json.dumps(out, ensure_ascii=False, indent=1)); print(ivd.to_string())
