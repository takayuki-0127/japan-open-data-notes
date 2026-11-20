"""873 平均の待ち時間が5分でも、10分以上待つ人は何%いるのか？（架空のデータ）

架空の店のレジ。店は1日600分（10時〜20時）開き、客はでたらめな間隔（ポアソン過程）で来て、
空いたレジに来た順に並ぶ。1人のレジにかかる時間（処理時間）も乱数。毎日、開店時は誰も並んでいない。
置き方ごとに、客の来る多さを「全員の待ち時間の平均がちょうど5分」になるように合わせてから、
10分以上待つ人の割合などを数える。
"""
import json, heapq
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 873
SRC = "架空の店のレジ（作成者が乱数で作成、seed 873）"
T_OPEN = 600.0          # 1日の営業時間（分）
N_DAYS = 400            # 1つの置き方で数える日数
TARGET = 5.0            # 合わせる平均の待ち時間（分）
GRID = np.linspace(0, T_OPEN, 6001)


def profile(kind):
    """時刻ごとの来客の多さ（1日の平均を1にした倍率）"""
    t = GRID
    if kind == "flat":
        p = np.ones_like(t)
    else:
        a = {"peak": 1.0, "peak_strong": 2.0}[kind]
        p = 1 + a * (0.8 * np.exp(-((t - 180) / 45) ** 2) + 0.6 * np.exp(-((t - 480) / 60) ** 2))
    return p / p.mean()


def cum(p):
    c = np.concatenate([[0], np.cumsum((p[1:] + p[:-1]) / 2 * np.diff(GRID))])
    return c


def draw_service(rng, n, mean, kind):
    if kind == "exp":
        return rng.exponential(mean, n)
    if kind == "const":
        return np.full(n, mean)
    if kind == "lognorm2":                     # ばらつきの大きい処理時間（変動係数2）
        cv = 2.0
        s2 = np.log(1 + cv ** 2)
        return rng.lognormal(np.log(mean) - s2 / 2, np.sqrt(s2), n)
    raise ValueError(kind)


def waits_fcfs(arr, svc, c):
    """来た順・c台のレジ。待ち時間（並んでからレジが始まるまで）"""
    n = len(arr)
    w = np.empty(n)
    if c == 1:
        free = 0.0
        for i in range(n):
            a = arr[i]
            st = a if a > free else free
            w[i] = st - a
            free = st + svc[i]
        return w
    h = [0.0] * c
    for i in range(n):
        a = arr[i]
        f = heapq.heappop(h)
        st = a if a > f else f
        w[i] = st - a
        heapq.heappush(h, st + svc[i])
    return w


class Setting:
    def __init__(self, key, label, c=1, svc_mean=2.0, svc_kind="exp", prof="flat", seed=0):
        self.key, self.label, self.c, self.svc_mean, self.svc_kind, self.prof = key, label, c, svc_mean, svc_kind, prof
        rng = np.random.default_rng(SEED * 100 + seed)
        p = profile(prof)
        self.C = cum(p)                            # 平均1の倍率の積分（0〜600）
        lam_max = 1.2 * c / svc_mean               # 探す上限（1分あたりの人数）
        umax = lam_max * self.C[-1]
        self.days = []
        for _ in range(N_DAYS):
            k = int(umax * 1.3 + 50)
            u = np.cumsum(rng.exponential(1.0, k))
            u = u[u <= umax]
            self.days.append((u, draw_service(rng, len(u), svc_mean, svc_kind)))

    def run(self, lam):
        out = []
        for d, (u, s) in enumerate(self.days):
            uu = u / lam
            m = uu <= self.C[-1]
            t = np.interp(uu[m], self.C, GRID)
            w = waits_fcfs(t.tolist(), s[m].tolist(), self.c)
            out.append(pd.DataFrame({"day": d, "arrival": t, "service": s[m], "wait": w}))
        return pd.concat(out, ignore_index=True)

    def calibrate(self):
        lo, hi = 0.05 * self.c / self.svc_mean, 1.15 * self.c / self.svc_mean
        for _ in range(26):
            mid = (lo + hi) / 2
            if self.run(mid)["wait"].mean() < TARGET:
                lo = mid
            else:
                hi = mid
        self.lam = (lo + hi) / 2
        self.df = self.run(self.lam)
        return self.df


def summarize(st, df):
    w = df["wait"].values
    busy = (df["service"].sum()) / (N_DAYS * T_OPEN * st.c)
    waited = w[w > 1e-9]
    return {"key": st.key, "label": st.label, "registers": st.c, "service_mean": st.svc_mean,
            "service_kind": st.svc_kind, "profile": st.prof,
            "arrivals_per_hour": round(st.lam * 60, 2), "customers": int(len(df)), "utilization": round(float(busy), 3),
            "mean_wait": round(float(w.mean()), 3), "share_no_wait": round(float((w <= 1e-9).mean()), 3),
            "median_wait": round(float(np.median(w)), 2), "p90_wait": round(float(np.quantile(w, .9)), 2),
            "p99_wait": round(float(np.quantile(w, .99)), 2),
            "share_ge5": round(float((w >= 5).mean()), 3), "share_ge10": round(float((w >= 10).mean()), 3),
            "share_ge15": round(float((w >= 15).mean()), 3), "share_ge20": round(float((w >= 20).mean()), 3),
            "mean_wait_if_waited": round(float(waited.mean()), 2),
            "day_share_ge10_p10": round(float(df.assign(g=w >= 10).groupby("day").g.mean().quantile(.1)), 3),
            "day_share_ge10_p90": round(float(df.assign(g=w >= 10).groupby("day").g.mean().quantile(.9)), 3)}


def main():
    settings = [
        Setting("base", "基本（レジ1台・処理2分・時刻で多さ一定）", seed=1),
        Setting("svc1", "処理1分", svc_mean=1.0, seed=2),
        Setting("svc4", "処理4分", svc_mean=4.0, seed=3),
        Setting("const", "処理時間が毎回同じ", svc_kind="const", seed=4),
        Setting("lognorm2", "処理時間のばらつき大（変動係数2）", svc_kind="lognorm2", seed=5),
        Setting("c3", "レジ3台（1つの列）", c=3, seed=6),
        Setting("peak", "昼と夕方に山", prof="peak", seed=7),
        Setting("peak_strong", "昼と夕方に強い山", prof="peak_strong", seed=8),
    ]
    rows, dfs = [], {}
    for st in settings:
        df = st.calibrate()
        dfs[st.key] = df
        rows.append(summarize(st, df))
    tab = pd.DataFrame(rows)
    tab.to_csv(RES / "settings.csv", index=False)

    # 理屈の値（ずっと開いている店・レジ1台・処理時間が指数分布のとき）：P(待ち≧t)=ρ·exp(−ρt/平均の待ち)
    theory = {}
    for sm in [1.0, 2.0, 4.0]:
        rho = TARGET / (TARGET + sm)
        theory[str(sm)] = {"rho": round(rho, 3), "share_no_wait": round(1 - rho, 3),
                           "share_ge10": round(rho * np.exp(-rho * 10 / TARGET), 3),
                           "mean_wait_if_waited": round(TARGET / rho, 2)}

    # 時刻ごと（昼と夕方に山）
    hour = {}
    for key in ["base", "peak", "peak_strong"]:
        d = dfs[key].assign(h=(dfs[key].arrival // 60).astype(int))
        g = d.groupby("h").agg(n=("wait", "size"), mean=("wait", "mean"), ge10=("wait", lambda x: (x >= 10).mean()))
        g["n"] = g["n"] / N_DAYS
        hour[key] = g.round(3)
    ht = pd.concat({k: v for k, v in hour.items()}, names=["setting", "hour_from_open"]).reset_index()
    ht.to_csv(RES / "by_hour.csv", index=False)

    # 1回分のデータ（基本の置き方の最初の30日）
    b = dfs["base"]
    b[b.day < 30].assign(customer_id=lambda x: np.arange(1, len(x) + 1))[
        ["customer_id", "day", "arrival", "service", "wait"]].to_csv(DATA / "customers_base_30days.csv", index=False,
                                                                     float_format="%.3f")

    pk = hour["peak"]
    out = {"target_mean_wait": TARGET, "days_per_setting": N_DAYS, "settings": rows, "theory_mm1_steady": theory,
           "peak_hours": {"busiest_hour_mean_wait": round(float(pk["mean"].max()), 2),
                          "busiest_hour_share_ge10": round(float(pk["ge10"].max()), 3),
                          "quietest_hour_mean_wait": round(float(pk["mean"].min()), 2),
                          "share_of_ge10_in_top3_hours": round(float(
                              (dfs["peak"].assign(h=(dfs["peak"].arrival // 60).astype(int))
                               .query("wait>=10").h.isin(pk["mean"].nlargest(3).index).mean())), 3)}}
    json.dump(out, open(RES / "a873_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：基本の置き方の待ち時間の分布
    w = b["wait"].values
    r0 = tab.set_index("key").loc["base"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    bins = np.arange(0, 41, 1)
    ax.hist(np.clip(w, 0, 40), bins=bins, color=LIGHT, weights=np.full(len(w), 100 / len(w)))
    ax.hist(np.clip(w[w >= 10], 0, 40), bins=bins[10:], color=ORANGE, weights=np.full((w >= 10).sum(), 100 / len(w)))
    ax.axvline(5, color=INK, lw=1, ls="--"); ax.text(5.4, ax.get_ylim()[1] * .9, "平均5分", fontsize=9)
    ax.text(0.98, 0.85, f"待たずに済んだ人 {r0.share_no_wait*100:.0f}%\n10分以上待った人 {r0.share_ge10*100:.0f}%"
            f"\n真ん中の人（中央値）{r0.median_wait:.1f}分", transform=ax.transAxes, ha="right", va="top", fontsize=9.5)
    ax.set_xlabel("待ち時間（分、40分以上は40に含める）"); ax.set_ylabel("客の割合（%）")
    ax.set_title("平均5分の店でも、待ち時間は0分と長い待ちに分かれる（レジ1台）")
    save(fig, "a873_hist.png", SRC)

    # 図2：置き方ごとの10分以上の割合
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    tt = tab.iloc[::-1]
    col = [ORANGE if k == "base" else BLUE for k in tt.key]
    ax.barh(tt.label, tt.share_ge10 * 100, color=col)
    for i, (v, z) in enumerate(zip(tt.share_ge10 * 100, tt.share_no_wait * 100)):
        ax.text(v + 0.4, i, f"{v:.0f}%（待ちなし{z:.0f}%）", va="center", fontsize=8.5)
    ax.set_xlim(0, max(tt.share_ge10 * 100) * 1.45)
    ax.set_xlabel("10分以上待った人の割合（%）。どれも全員の平均の待ちは5分")
    ax.set_title(f"8通りの置き方で、10分以上待つ人は{tab.share_ge10.min()*100:.0f}〜{tab.share_ge10.max()*100:.0f}%とほぼ同じ（待ちなしは大きく違う）")
    save(fig, "a873_settings.png", SRC)

    # 図3：昼と夕方に山がある店の時刻ごと
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    x = pk.index.values
    ax.bar(x, pk["ge10"] * 100, color=BLUE, width=.7, label="10分以上待った人の割合（%）")
    ax.plot(x, pk["mean"], color=ORANGE, marker="o", label="平均の待ち時間（分）")
    ax.axhline(5, color=GRAY, lw=1, ls="--")
    ax.set_xticks(x); ax.set_xticklabels([f"{10+h}時台" for h in x], fontsize=8.5)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("1日の平均は5分でも、混む時間帯には平均も長い待ちも集まる（昼と夕方に山）")
    save(fig, "a873_hour.png", SRC)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
