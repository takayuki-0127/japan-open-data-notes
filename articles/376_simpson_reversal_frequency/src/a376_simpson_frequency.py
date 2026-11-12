"""A376 全体では下がっているのに、どの区分でも上がっていることは、どれくらい起きるのか
手元にある公的統計の「区分つきの率」で、全体の向きと区分ごとの向きが逆になる回数を数える。
あわせて架空の構成で、構成がどれだけ動くと逆になるかを数える。乱数の種は376。
"""
import json, itertools
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import DATA, FIG, RES, BLUE, ORANGE, GRAY, INK, LIGHT, GREEN, save

SEED = 376
RAW = DATA / "raw"
SRC = "総務省「住宅・土地統計調査」、警察庁の交通事故統計、厚生労働省「都道府県別生命表」「医療保険に関する基礎資料」「人口動態統計」ほか（詳しくは README）をもとに作成"


# ---------- 1. 手元の系列を「年 × 区分 の 率 と 重み」の形にそろえる ----------
def owner():
    d = pd.read_csv(RAW / "owner_by_age_long_297.csv"); d = d[(d.year >= 1978) & (d.age != "総数")].copy()
    def band(a):
        return "65歳以上" if a[:2] in ("65", "70", "75", "80", "85") else a
    out = []
    for y, g in d.groupby("year"):
        if (g.age == "65歳以上").any(): g = g[~g.age.str[:2].isin(["70", "75", "80", "85"]) & (g.age != "65～69歳") & (g.age != "65～74歳")]
        g = g.assign(seg=g.age.map(band)).groupby("seg")[["total", "owned"]].sum().reset_index()
        g["year"] = y; out.append(g)
    d = pd.concat(out); d["rate"] = d.owned / d.total * 100; d["w"] = d.total
    return {("持ち家率（世帯主の年齢10区分）", "全国"): d[["year", "seg", "rate", "w"]]}


def police():
    d = pd.read_csv(RAW / "police_age_year_main_F264.csv"); d = d[d.age != "合計"]
    out = {}
    for (k, ed), g in d.groupby(["kind", "edition"]):
        name = ("人身事故" if k == "all" else "死亡事故") + "の率（免許保有者あたり、年齢15区分）"
        out[(name, "全国 " + ("2009〜14年" if ed == "2019ed" else "2015〜25年"))] = g.rename(columns={"age": "seg", "lic": "w"})[["year", "seg", "rate", "w"]]
    return out


def mortality():
    d = pd.read_csv(RAW / "mortality_cells_F62.csv")
    out = {}
    for (p, s), g in d.groupby(["pref", "sex"]):
        g = g.assign(rate=g.m * 1000).rename(columns={"age": "seg", "pop": "w"})
        out[("死亡率（年齢19区分）", f"{p}・{s}")] = g[["year", "seg", "rate", "w"]]
    return out


def medical():
    d = pd.read_csv(RAW / "medical_panel_F280.csv").rename(columns={"fy": "year", "age": "seg", "cost_man": "rate", "pop_k": "w"})
    return {("1人当たり医療費（年齢21区分）", "全国"): d[["year", "seg", "rate", "w"]]}


def births():
    b = pd.read_csv(RAW / "births_by_age_F262.csv"); w = pd.read_csv(RAW / "women_by_age_F262.csv")
    w = w[w.source.isin(["estimate", "census2025"])]
    cols = ["a15", "a20", "a25", "a30", "a35", "a40", "a45"]
    m = b.merge(w, on="year", suffixes=("_b", "_w"))
    rows = []
    for _, r in m.iterrows():
        for c in cols: rows.append((int(r.year), c[1:] + "〜", r[c + "_b"] / r[c + "_w"] * 1000, r[c + "_w"]))
    return {("出生率（15〜49歳の女性あたり、年齢7区分）", "全国"): pd.DataFrame(rows, columns=["year", "seg", "rate", "w"])}


def windows():
    d = pd.read_csv(RAW / "energy_equipment_long_304.csv"); d = d[d.tenure != "総数"]
    p = d.pivot_table(index=["area", "year", "tenure"], columns="item", values="dwellings").reset_index()
    p["rate"] = (p.win_all + p.win_some) / p.total * 100
    out = {}
    for a, g in p.groupby("area"):
        out[("二重サッシ・複層ガラスの窓がある住宅の割合（持ち家・借家）", a)] = g.rename(columns={"tenure": "seg", "total": "w"})[["year", "seg", "rate", "w"]]
    return out


def compare(tab, y0, y1):
    a = tab[tab.year == y0].set_index("seg"); b = tab[tab.year == y1].set_index("seg")
    seg = a.index.intersection(b.index)
    a, b = a.loc[seg], b.loc[seg]
    w0, w1 = a.w / a.w.sum(), b.w / b.w.sum()
    all0, all1 = (w0 * a.rate).sum(), (w1 * b.rate).sum()
    dr = b.rate - a.rate
    tol = 1e-9
    up, down = int((dr > tol).sum()), int((dr < -tol).sum())
    d_all = all1 - all0
    within = ((w0 + w1) / 2 * dr).sum()            # 区分の中の変化（構成は2時点の平均で固定）
    between = ((a.rate + b.rate) / 2 * (w1 - w0)).sum()   # 構成の変化
    strict = (d_all < 0 and down == 0 and up > 0) or (d_all > 0 and up == 0 and down > 0)
    return dict(y0=y0, y1=y1, n_seg=len(seg), all0=all0, all1=all1, d_all=d_all, up=up, down=down,
                within=within, between=between, strict=bool(strict), sign_flip=bool(d_all * within < 0),
                shift=float(0.5 * np.abs(w1 - w0).sum() * 100))


def main():
    series = {}
    for f in (owner, police, mortality, medical, births, windows): series.update(f())
    rows = []
    for (name, area), tab in series.items():
        years = sorted(tab.year.unique())
        for y0, y1 in itertools.combinations(years, 2):
            r = compare(tab, y0, y1); r.update(series=name, area=area, adjacent=(years.index(y1) - years.index(y0) == 1)); rows.append(r)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "comparisons.csv", index=False)

    def summ(g):
        return pd.Series({"比べた回数": len(g), "全体と区分の向きがすべて逆": int(g.strict.sum()), "割合_すべて逆(%)": round(g.strict.mean() * 100, 1),
                          "全体と区分の中の変化の向きが逆": int(g.sign_flip.sum()), "割合_向きが逆(%)": round(g.sign_flip.mean() * 100, 1),
                          "構成の動き_中央値(ポイント)": round(g["shift"].median(), 1)})
    by = df.groupby("series", sort=False).apply(summ).reset_index()
    by_adj = df[df.adjacent].groupby("series", sort=False).apply(summ).reset_index()
    by.to_csv(RES / "by_series_all_pairs.csv", index=False); by_adj.to_csv(RES / "by_series_adjacent.csv", index=False)

    # 例：全国の死亡率（男女計に近い見方として、男・女それぞれ）と持ち家率
    ex = df[(df.series.str.startswith("死亡率")) & (df.area.str.startswith("全国")) & (df.y0 == 2010) & (df.y1 == 2020)]
    own = df[df.series.str.startswith("持ち家率")]

    # ---------- 2. 架空の構成：構成がどれだけ動くと逆になるか ----------
    rng = np.random.default_rng(SEED)
    K, REPS = 10, 4000
    shifts = np.arange(0, 21, 1.0)          # 構成の動き（ポイント。移った人の割合）
    ratios = [2, 5, 10, 20]                 # 区分のあいだの率の差（標準偏差）÷ 区分の中の変化
    sim = []
    for mode in ("aligned", "random"):
        for R in ratios:
            for s in shifts:
                flips = 0
                for _ in range(REPS // 4 if mode == "random" else REPS // 4):
                    r0 = rng.normal(0, R, K)                    # 区分ごとの率（区分の中の変化を1とした単位）
                    w0 = rng.dirichlet(np.full(K, 5.0))
                    dr = np.clip(rng.normal(1.0, 0.3, K), 0.05, None)   # どの区分でも上がる（+1 前後）
                    if mode == "aligned":                        # 率の高い区分から低い区分へ人が移る
                        v = -(r0 - (w0 * r0).sum())
                    else:                                        # 率と関係なく移る
                        v = rng.normal(0, 1, K)
                    v = v - v.mean(); v = v / (0.5 * np.abs(v).sum())
                    w1 = np.clip(w0 + s / 100 * v, 1e-6, None); w1 = w1 / w1.sum()
                    d_all = (w1 * (r0 + dr)).sum() - (w0 * r0).sum()
                    flips += d_all < 0
                n = REPS // 4
                sim.append(dict(mode=mode, ratio=R, shift=s, p_reverse=flips / n * 100))
    sim = pd.DataFrame(sim); sim.to_csv(RES / "simulation.csv", index=False)

    # 実際の系列での「率の差 ÷ 区分の中の変化」と構成の動き
    out = {"n_series": len(series), "n_comparisons": int(len(df)), "n_adjacent": int(df.adjacent.sum()),
           "strict_all": int(df.strict.sum()), "strict_all_pct": round(df.strict.mean() * 100, 1),
           "strict_adjacent": int(df[df.adjacent].strict.sum()), "strict_adjacent_pct": round(df[df.adjacent].strict.mean() * 100, 1),
           "sign_flip_all": int(df.sign_flip.sum()), "sign_flip_all_pct": round(df.sign_flip.mean() * 100, 1),
           "sign_flip_adjacent": int(df[df.adjacent].sign_flip.sum()), "sign_flip_adjacent_pct": round(df[df.adjacent].sign_flip.mean() * 100, 1),
           "mortality_national_2010_2020": ex[["area", "all0", "all1", "up", "down", "within", "between", "strict", "shift"]].round(3).to_dict("records"),
           "owner_pairs": own[["y0", "y1", "all0", "all1", "up", "down", "within", "between", "strict", "sign_flip", "shift"]].round(2).to_dict("records"),
           "sim_aligned_50pct_shift": {str(R): float(sim[(sim["mode"] == "aligned") & (sim.ratio == R) & (sim.p_reverse >= 50)]["shift"].min()) if (sim[(sim["mode"] == "aligned") & (sim.ratio == R)].p_reverse >= 50).any() else None for R in ratios}}
    # 系列のなかで逆転が起きた割合（死亡率は地域×男女の96系列）
    mort = df[df.series.str.startswith("死亡率")]
    out["mortality_by_period"] = {f"{a}-{b}": {"n": int(len(g)), "strict": int(g.strict.sum()), "sign_flip": int(g.sign_flip.sum())} for (a, b), g in mort.groupby(["y0", "y1"])}
    json.dump(out, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)
    print(by.to_string()); print(by_adj.to_string()); print(json.dumps({k: v for k, v in out.items() if k not in ("owner_pairs",)}, ensure_ascii=False, indent=1))
    print(own[["y0", "y1", "all0", "all1", "up", "down", "within", "between", "strict", "sign_flip"]].round(2).to_string())

    # ---------- 図 ----------
    # 図1：全国の死亡率（女）2010→2020：年齢ごとの変化率と全体
    t = series[("死亡率（年齢19区分）", "全国・女")]
    a = t[t.year == 2010].set_index("seg"); b = t[t.year == 2020].set_index("seg")
    chg = (b.rate / a.rate - 1) * 100
    allchg = ((b.w / b.w.sum() * b.rate).sum() / (a.w / a.w.sum() * a.rate).sum() - 1) * 100
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar(range(len(chg)), chg.values, color=BLUE)
    ax.bar([len(chg) + 0.6], [allchg], color=ORANGE)
    ax.axhline(0, color=INK, lw=0.8)
    ax.set_xticks(list(range(len(chg))) + [len(chg) + 0.6]); ax.set_xticklabels(list(chg.index) + ["全体"], rotation=60, fontsize=8)
    ax.set_ylabel("死亡率の変化（2010→2020年、%）")
    ax.set_title(f"どの年齢でも下がったのに、全体は{allchg:+.0f}%（全国・女）")
    ax.text(len(chg) + 0.6, allchg + 1, f"{allchg:+.1f}%", ha="center", color=ORANGE, fontsize=10)
    save(fig, "a376_example_mortality.png", "厚生労働省「都道府県別生命表」、国立社会保障・人口問題研究所の基準人口をもとに作成（F62 の写し）")

    # 図2：系列ごとの「逆」の割合（すべての年の組）
    fig, ax = plt.subplots(figsize=(9, 4.4))
    lab = [s.split("（")[0] for s in by.series]; y = np.arange(len(by))
    ax.barh(y - 0.2, by["割合_向きが逆(%)"], 0.4, color=LIGHT, label="全体の向きと、区分の中の変化の向きが逆")
    ax.barh(y + 0.2, by["割合_すべて逆(%)"], 0.4, color=ORANGE, label="全体の向きと、すべての区分の向きが逆")
    for i, r in by.iterrows():
        ax.text(r["割合_向きが逆(%)"] + 1, i - 0.2, f"{r['割合_向きが逆(%)']:.0f}%（{int(r['全体と区分の中の変化の向きが逆'])}/{int(r['比べた回数'])}）", va="center", fontsize=8)
        ax.text(r["割合_すべて逆(%)"] + 1, i + 0.2, f"{r['割合_すべて逆(%)']:.0f}%", va="center", fontsize=8, color=ORANGE)
    ax.set_yticks(y); ax.set_yticklabels(lab, fontsize=9); ax.invert_yaxis(); ax.set_xlim(0, 115)
    ax.set_xlabel("年の組のうち、逆になった割合（%）"); ax.legend(fontsize=8, loc="lower right", frameon=False)
    ax.set_title("逆になるのは、構成が大きく動く系列に集まっていた")
    save(fig, "a376_frequency_by_series.png", SRC)

    # 図3：架空の構成
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    cols = {2: GRAY, 5: LIGHT, 10: BLUE, 20: ORANGE}
    for ax, mode, ttl in zip(axes, ("aligned", "random"), ("率の高い区分から低い区分へ人が移る", "率と関係なく人が移る")):
        for R in ratios:
            g = sim[(sim["mode"] == mode) & (sim.ratio == R)]
            ax.plot(g["shift"], g.p_reverse, color=cols[R], lw=2, label=f"区分の差が、中の変化の{R}倍")
        ax.set_title(ttl, fontsize=11); ax.set_xlabel("構成の動き（移った人の割合、ポイント）")
    axes[0].set_ylabel("全体が逆向きになった割合（%）"); axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("どの区分も上がっているのに全体が下がる割合（架空の10区分）", fontsize=12)
    save(fig, "a376_simulation.png", "架空のデータ（作成者が乱数で作成、seed 376）")


if __name__ == "__main__":
    main()
