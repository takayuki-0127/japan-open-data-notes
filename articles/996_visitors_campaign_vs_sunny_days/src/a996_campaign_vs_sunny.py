"""996 天気のよい日と比べた「集客の効果」は、何を読み違えるのか？（架空のデータ）

架空の屋外の庭園「Aガーデン」の1年（364日＝2週間の区切り26個）。1日の来場者は、曜日（平日・土日）と
天気（晴れ・くもり・雨）で決まる見込みに、日ごとの振れを掛けたもの（作成者が置く）。
26個の区切りのうち半分（13個）で、1日だけ集客のキャンペーンを行う。キャンペーンの日を選ぶ人は、
天気予報が晴れの日と土日を選びやすい。キャンペーンの日は来場者が増えるが、増えた分の一部は、
同じ区切りのほかの日に来るはずだった人が移ってきただけ（作成者が置く）。
キャンペーンの本当の効果（その日に増えた人数と、区切り全体で差し引き増えた人数）を作成者が知っているので、
比べ方ごとの見積もりがどれだけずれるかを数える。
"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import RES, DATA, save, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN

SEED = 996
SRC = "架空の庭園の来場者（作成者が乱数で作成、seed 996）"
N_BLOCK, BLOCK = 26, 14
N_DAY = N_BLOCK * BLOCK
BASE_WEEKDAY, BASE_WEEKEND = 1000.0, 1800.0
WEATHER = ["晴れ", "くもり", "雨"]
W_PROB = [0.5, 0.3, 0.2]
W_MULT = {"晴れ": 1.0, "くもり": 0.75, "雨": 0.35}
FORECAST_HIT = 0.8      # 予報が当たる確率（外れたときは3つから同じ確率で選び直す）
NOISE_SD = 0.12          # 日ごとの振れ（対数の標準偏差）
LIFT = 0.20              # キャンペーンの日に増える割合（その日の見込みに対して）
DISPLACE = 0.5           # 増えた分のうち、同じ区切りのほかの日から移ってきた割合
SELECT = 3.0             # 晴れの予報・土日を選ぶ強さ（0ならでたらめに選ぶ）
REPS = 200

METHODS = [("m1_plain", "① そのまま（キャンペーンの日とほかの日）"),
           ("m2_sunny", "② 晴れの日どうし"),
           ("m3_cell", "③ 天気と曜日をそろえる"),
           ("m4_cell_clean", "④ ③をキャンペーンのない区切りの日とだけ"),
           ("m5_block", "⑤ 区切りの合計で比べる")]


def one_year(rng, lift=LIFT, displace=DISPLACE, select=SELECT, rain_mult=W_MULT["雨"]):
    mult = {"晴れ": 1.0, "くもり": 0.75, "雨": rain_mult}
    day = np.arange(N_DAY)
    weekend = (day % 7 >= 5).astype(int)
    wi = rng.choice(3, N_DAY, p=W_PROB)
    hit = rng.random(N_DAY) < FORECAST_HIT
    fi = np.where(hit, wi, rng.choice(3, N_DAY))
    weather = np.array(WEATHER)[wi]
    forecast = np.array(WEATHER)[fi]
    expected = np.where(weekend == 1, BASE_WEEKEND, BASE_WEEKDAY) * np.array([mult[w] for w in weather])
    base = expected * np.exp(rng.normal(0, NOISE_SD, N_DAY))       # キャンペーンがなかったときの来場者
    block = day // BLOCK
    camp_blocks = rng.choice(N_BLOCK, N_BLOCK // 2, replace=False)
    campaign = np.zeros(N_DAY, int)
    visitors = base.copy()
    on_extra, net_extra = [], []
    fscore = np.array([{"晴れ": 1.0, "くもり": 0.5, "雨": 0.0}[f] for f in forecast]) + weekend
    for b in camp_blocks:
        idx = np.where(block == b)[0]
        w = np.exp(select * fscore[idx]); w /= w.sum()
        c = rng.choice(idx, p=w)
        campaign[c] = 1
        extra = lift * base[c]
        visitors[c] += extra
        others = idx[idx != c]
        visitors[others] -= displace * extra * base[others] / base[others].sum()
        on_extra.append(extra)
        net_extra.append(extra * (1 - displace))
    df = pd.DataFrame({"day": day + 1, "block": block + 1, "weekend": weekend, "weather": weather, "forecast": forecast,
                       "campaign": campaign, "block_has_campaign": np.isin(block, camp_blocks).astype(int),
                       "no_campaign_visitors": base, "visitors": visitors})
    truth = {"on_day_extra": float(np.mean(on_extra)), "net_extra": float(np.mean(net_extra))}
    return df, truth


def estimates(df):
    v, c = df.visitors.values, df.campaign.values == 1
    out = {"m1_plain": v[c].mean() - v[~c].mean()}
    sun = df.weather.values == "晴れ"
    out["m2_sunny"] = v[c & sun].mean() - v[~c & sun].mean() if (c & sun).any() else np.nan
    cell = df.weather + "_" + df.weekend.astype(str)

    def cell_est(ctrl):
        means = df[ctrl].groupby(cell[ctrl]).visitors.mean()
        d = [v[i] - means.get(cell.iloc[i], np.nan) for i in np.where(c)[0]]
        return float(np.nanmean(d))
    out["m3_cell"] = cell_est(~c)
    clean = (df.block_has_campaign.values == 0)
    out["m4_cell_clean"] = cell_est(clean)
    # ⑤ 区切りの合計：キャンペーンのない区切りの日で、天気と曜日ごとの平均を出し、
    #   キャンペーンのある区切りの見込みの合計と、実際の合計の差を、キャンペーン1回あたりにする
    means = df[clean].groupby(cell[clean]).visitors.mean()
    cb = df.block_has_campaign.values == 1
    pred = cell[cb].map(means).values
    out["m5_block"] = float((v[cb].sum() - np.nansum(pred)) / c.sum())
    out["campaign_sunny_pct"] = float((df.weather[c] == "晴れ").mean() * 100)
    out["campaign_weekend_pct"] = float(df.weekend[c].mean() * 100)
    out["other_sunny_weekend_pct"] = float(df.weekend[~c & sun].mean() * 100)
    out["campaign_sunny_weekend_pct"] = float(df.weekend[c & sun].mean() * 100) if (c & sun).any() else np.nan
    return out


def run(rng, reps, **kw):
    rows = []
    for _ in range(reps):
        df, t = one_year(rng, **kw)
        e = estimates(df)
        e.update(t)
        rows.append(e)
    return pd.DataFrame(rows)


def main():
    rng = np.random.default_rng(SEED)
    df1, t1 = one_year(np.random.default_rng(SEED * 10))
    df1.round(1).to_csv(DATA / "days.csv", index=False)
    e1 = estimates(df1)

    sim = run(rng, REPS)
    sim.round(3).to_csv(RES / "base_200reps.csv", index=False)
    base = {}
    for k, _ in METHODS:
        x = sim[k]
        base[k] = {"mean": round(float(x.mean()), 1), "p10": round(float(x.quantile(0.1)), 1),
                   "p90": round(float(x.quantile(0.9)), 1),
                   "ratio_to_net": round(float(x.mean() / sim.net_extra.mean()), 3),
                   "ratio_to_on_day": round(float(x.mean() / sim.on_day_extra.mean()), 3)}
    truth = {"on_day_extra": round(float(sim.on_day_extra.mean()), 1), "net_extra": round(float(sim.net_extra.mean()), 1)}
    mix = {k: round(float(sim[k].mean()), 2) for k in
           ["campaign_sunny_pct", "campaign_weekend_pct", "other_sunny_weekend_pct", "campaign_sunny_weekend_pct"]}

    # 倍率は「見積もりの平均÷本当の差し引きの平均」
    # 確かめ：移ってきた割合 × 晴れ・土日を選ぶ強さ × 増える割合（27通り、各100回）
    grid = []
    for d in [0.0, 0.5, 0.8]:
        for s in [0.0, 3.0, 6.0]:
            for L in [0.1, 0.2, 0.4]:
                g = run(np.random.default_rng(SEED * 1000 + int(d * 10) * 100 + int(s) * 10 + int(L * 10)), 100,
                        lift=L, displace=d, select=s)
                row = {"displace": d, "select": s, "lift": L,
                       "on_day_extra": round(float(g.on_day_extra.mean()), 1), "net_extra": round(float(g.net_extra.mean()), 1)}
                for k, _ in METHODS:
                    row[k] = round(float(g[k].mean()), 1)
                    row[k + "_ratio_net"] = round(float(g[k].mean() / g.net_extra.mean()), 3)
                grid.append(row)
    grid = pd.DataFrame(grid)
    grid.to_csv(RES / "grid_displace_select_lift.csv", index=False)
    # 確かめ：雨の日の減り方（0.35 → 0.6、0.15）
    rain = []
    for rm in [0.15, 0.35, 0.6]:
        g = run(np.random.default_rng(SEED * 7 + int(rm * 100)), 100, rain_mult=rm)
        row = {"rain_mult": rm, "net_extra": round(float(g.net_extra.mean()), 1)}
        for k, _ in METHODS:
            row[k] = round(float(g[k].mean()), 1)
            row[k + "_ratio_net"] = round(float(g[k].mean() / g.net_extra.mean()), 3)
        rain.append(row)
    rain = pd.DataFrame(rain)
    rain.to_csv(RES / "by_rain_mult.csv", index=False)

    gd = grid[grid.displace > 0]
    out = {"setting": {"days": N_DAY, "blocks": N_BLOCK, "block_days": BLOCK, "campaigns": N_BLOCK // 2,
                       "base_weekday": BASE_WEEKDAY, "base_weekend": BASE_WEEKEND, "weather_prob": dict(zip(WEATHER, W_PROB)),
                       "weather_mult": W_MULT, "forecast_hit": FORECAST_HIT, "noise_sd": NOISE_SD, "lift": LIFT,
                       "displace": DISPLACE, "select": SELECT, "reps": REPS},
           "truth_200reps": truth, "estimates_200reps": base, "mix_200reps": mix,
           "formula": {"on_day_over_net": round(1 / (1 - DISPLACE), 3)},
           "first_year": {"truth": {k: round(v, 1) for k, v in t1.items()},
                          "estimates": {k: round(float(v), 1) for k, v in e1.items()}},
           "grid_info": {"cases": int(len(grid)), "reps_each": 100},
           "grid_range_ratio_net": {k: [float(grid[k + "_ratio_net"].min()), float(grid[k + "_ratio_net"].max())]
                                    for k, _ in METHODS},
           "grid_range_ratio_net_displace_gt0": {k: [float(gd[k + "_ratio_net"].min()), float(gd[k + "_ratio_net"].max())]
                                                 for k, _ in METHODS},
           "grid_summary": [{"displace": float(d), "select": ("でたらめ" if sel else "選びやすい（3・6）"),
                             **{k + "_ratio_net": [float(gg[k + "_ratio_net"].min()), float(gg[k + "_ratio_net"].max())]
                                for k, _ in METHODS}}
                            for d in [0.0, 0.5, 0.8] for sel in [True, False]
                            for gg in [grid[(grid.displace == d) & ((grid.select == 0) == sel)]]],
           "grid_m2_gt_net_cases": int((grid.m2_sunny_ratio_net > 1).sum()),
           "rain": rain.to_dict("records")}
    json.dump(out, open(RES / "a996_main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # 図1：1年のうち8週の来場者（天気で色分け、キャンペーンの日に印）
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    sub = df1[(df1.day > 0) & (df1.day <= 56)]
    col = {"晴れ": ORANGE, "くもり": GRAY, "雨": BLUE}
    for w in WEATHER:
        s = sub[sub.weather == w]
        ax.bar(s.day, s.visitors, color=col[w], width=0.8, label=w)
    cs = sub[sub.campaign == 1]
    ax.plot(cs.day, cs.visitors + 120, "v", color=INK, ms=8, label="キャンペーンの日")
    for b in range(1, 5):
        ax.axvline(b * BLOCK + 0.5, color=GRAY, lw=0.6, ls=":")
    ax.set_xlabel("日（1年のうち最初の8週。点線は2週間の区切り）"); ax.set_ylabel("来場者（人）")
    ax.legend(frameon=False, fontsize=8.5, ncol=4, loc="upper left")
    ax.set_ylim(0, sub.visitors.max() * 1.25)
    ax.set_title("キャンペーンの日は、晴れの土日に選ばれやすい（1年分のうち8週）", fontsize=12)
    save(fig, "a996_days.png", SRC)

    # 図2：比べ方ごとの見積もり（200回の平均と10〜90%）
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    y = np.arange(len(METHODS))[::-1]
    for yy, (k, lab) in zip(y, METHODS):
        b = base[k]
        ax.barh(yy, b["mean"], color=ORANGE if k in ("m1_plain", "m2_sunny") else BLUE, height=0.6)
        ax.plot([b["p10"], b["p90"]], [yy, yy], color=INK, lw=1.2)
        ax.text(max(b["p90"], b["mean"]) + 15, yy, f"{b['mean']:.0f}人", va="center", fontsize=9)
    ax.axvline(truth["net_extra"], color=GREEN, lw=2, ls="--")
    ax.text(truth["net_extra"] - 8, -0.75, f"本当の差し引き {truth['net_extra']:.0f}人", color=GREEN, fontsize=9, ha="right")
    ax.axvline(truth["on_day_extra"], color=GRAY, lw=1.5, ls=":")
    ax.text(truth["on_day_extra"] + 8, -0.75, f"その日に増えた {truth['on_day_extra']:.0f}人", color=GRAY, fontsize=9, ha="left")
    ax.set_yticks(y); ax.set_yticklabels([lab for _, lab in METHODS], fontsize=9)
    ax.set_xlabel("キャンペーン1回で増えた人数の見積もり（人。線は10〜90%）")
    ax.set_ylim(-1.1, len(METHODS) - 0.1)
    ax.set_title("比べ方で、キャンペーンの効果の見積もりが変わる（200回の平均）", fontsize=12)
    save(fig, "a996_estimates.png", SRC)

    # 図3：確かめ。②晴れの日どうし÷本当の差し引き（移ってきた割合×選ぶ強さ、増える割合20%）
    fig, ax = plt.subplots(figsize=(7.6, 3.9))
    x = np.arange(3); bw = 0.26
    for j, (s, c) in enumerate([(0.0, LIGHT), (3.0, BLUE), (6.0, ORANGE)]):
        g = grid[(grid.select == s) & (grid.lift == 0.2)]
        ax.bar(x + (j - 1) * bw, g.m2_sunny_ratio_net, bw, color=c,
               label={0.0: "でたらめに選ぶ", 3.0: "晴れ・土日を選びやすい（基本）", 6.0: "とても選びやすい"}[s])
        for i, v in enumerate(g.m2_sunny_ratio_net):
            ax.text(i + (j - 1) * bw, v + 0.08, f"{v:.2f}", ha="center", fontsize=8)
    ax.axhline(1, color=GREEN, lw=1.2, ls="--")
    ax.set_xticks(x); ax.set_xticklabels([f"移ってきた割合 {int(d * 100)}%" for d in [0, 0.5, 0.8]], fontsize=9.5)
    ax.set_xlabel("キャンペーンで増えた分のうち、同じ区切りのほかの日から移ってきた割合", fontsize=9.5)
    ax.set_ylabel("②晴れの日どうし ÷ 本当の差し引き（倍）")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.set_title("晴れの日どうしの比べ方は、移ってきた人と土日の偏りの分だけ大きく出る\n（増える割合20%、各100回）", fontsize=12)
    save(fig, "a996_grid.png", SRC)

    print(json.dumps({k: out[k] for k in out if k != "rain"}, ensure_ascii=False, indent=1))
    print(grid.to_string()); print(rain.to_string())


if __name__ == "__main__":
    main()
