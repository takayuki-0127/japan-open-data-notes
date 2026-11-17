"""03 分析：円建ての割合の推移、地域別、シフト・シェア分解、ドル円との相関、頑健性。
出力：results/main.json, results/jpy_share.csv, results/shift_share.csv, results/robustness.csv
"""
import json, pathlib
import numpy as np
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "results"
R.mkdir(exist_ok=True)
AR = ["USA", "EU", "ASIA", "OTHER"]


def table(c, flow, cur):
    t = c[(c.flow == flow) & (c.currency == cur)].pivot(index="half", columns="area", values="share")
    return t


def shift_share(js, w, h0, h1):
    s0 = js.loc[h0, AR]; s1 = js.loc[h1, AR]; w0 = w.loc[h0, AR]; w1 = w.loc[h1, AR]
    within = float(((s1 - s0) * (w0 + w1) / 2).sum()); comp = float(((w1 - w0) * (s0 + s1) / 2).sum())
    return dict(h0=h0, h1=h1, total=float((s1 * w1).sum() - (s0 * w0).sum()), within=within, composition=comp)


def main():
    c = pd.read_csv(D / "currency_long.csv")
    ex = pd.read_csv(D / "exports_half.csv").set_index("half")
    fx = pd.read_csv(D / "fx_half.csv").set_index("half").usdjpy
    je = table(c, "export", "JPY"); ue = table(c, "export", "USD"); ji = table(c, "import", "JPY")
    core = je[["WORLD", "USA", "EU", "ASIA"]].dropna()
    w = ex.loc[core.index, AR].div(ex.loc[core.index, "WORLD"], axis=0)
    # その他の地域の円の割合を逆算
    core = core.copy()
    core["OTHER"] = (core.WORLD - (w[["USA", "EU", "ASIA"]] * core[["USA", "EU", "ASIA"]]).sum(axis=1)) / w.OTHER
    out = core.join(ue[["WORLD", "ASIA", "USA"]].add_prefix("usd_")).join(ji[["WORLD", "USA", "EU", "ASIA"]].add_prefix("imp_jpy_")).join(fx)
    out = out.join(w.add_prefix("w_"))
    out.round(4).to_csv(R / "jpy_share.csv")
    h0, h1 = core.index[0], core.index[-1]
    ss = shift_share(core, w, h0, h1)
    d_share = core.WORLD.diff(); d_fx = np.log(fx.loc[core.index]).diff()
    ok = d_share.notna() & d_fx.notna()
    corr = float(np.corrcoef(d_share[ok], d_fx[ok])[0, 1])
    main = dict(first=h0, last=h1, world_first=float(core.loc[h0, "WORLD"]), world_last=float(core.loc[h1, "WORLD"]),
                world_min=float(core.WORLD.min()), world_min_half=core.WORLD.idxmin(), world_max=float(core.WORLD.max()), world_max_half=core.WORLD.idxmax(),
                world_mean=float(core.WORLD.mean()),
                **{f"{a.lower()}_first": float(core.loc[h0, a]) for a in ["USA", "EU", "ASIA", "OTHER"]},
                **{f"{a.lower()}_last": float(core.loc[h1, a]) for a in ["USA", "EU", "ASIA", "OTHER"]},
                usd_world_first=float(ue.loc[h0, "WORLD"]), usd_world_last=float(ue.loc[h1, "WORLD"]),
                usd_asia_first=float(ue.loc[h0, "ASIA"]), usd_asia_last=float(ue.loc[h1, "ASIA"]),
                imp_world_first=float(ji.loc[h0, "WORLD"]), imp_world_last=float(ji.loc[h1, "WORLD"]),
                imp_world_min=float(ji.WORLD.min()), imp_world_max=float(ji.WORLD.max()),
                imp_below_exp_all=bool((ji.WORLD.loc[core.index] < core.WORLD).all()),
                w_asia_first=float(w.loc[h0, "ASIA"]), w_asia_last=float(w.loc[h1, "ASIA"]),
                w_usa_first=float(w.loc[h0, "USA"]), w_usa_last=float(w.loc[h1, "USA"]),
                ss_total=ss["total"], ss_within=ss["within"], ss_composition=ss["composition"], corr_dshare_dfx=corr,
                usdjpy_first=float(fx.loc[h0]), usdjpy_last=float(fx.loc[h1]))
    main["asia_change"] = main["asia_last"] - main["asia_first"]
    main["H1"] = "支持" if (core.WORLD.min() >= 33 and core.WORLD.max() <= 42) else "外れ"
    main["H2"] = "支持" if main["asia_change"] <= -5 else "外れ"
    main["H3"] = "支持" if abs(ss["within"]) > abs(ss["composition"]) else "外れ"
    main["H4"] = "支持" if abs(corr) < 0.3 else "外れ"
    rob = []
    for a, b in [(h0, h1), ("2001H1", h1), ("2012H2", h1)]:
        s = shift_share(core, w, a, b)
        rob.append(dict(check=f"シフト・シェア {a}→{b}", total=s["total"], within=s["within"], composition=s["composition"], asia_change=float(core.loc[b, "ASIA"] - core.loc[a, "ASIA"])))
    f6 = core.iloc[:6].mean(); l6 = core.iloc[-6:].mean()
    rob.append(dict(check="最初と最後の6半期の平均の差", total=float(l6.WORLD - f6.WORLD), within=np.nan, composition=np.nan, asia_change=float(l6.ASIA - f6.ASIA)))
    lv = float(np.corrcoef(core.WORLD, np.log(fx.loc[core.index]))[0, 1])
    lag = d_share.shift(-1); ok2 = lag.notna() & d_fx.notna()
    lagc = float(np.corrcoef(lag[ok2], d_fx[ok2])[0, 1])
    rob.append(dict(check="相関：水準どうし（円の割合と log ドル円）", total=lv, within=np.nan, composition=np.nan, asia_change=np.nan))
    rob.append(dict(check="相関：ドル円の変化と次の半期の円の割合の変化", total=lagc, within=np.nan, composition=np.nan, asia_change=np.nan))
    rob.append(dict(check="輸入：世界の円の割合 最初→最後の変化", total=float(ji.loc[h1, "WORLD"] - ji.loc[h0, "WORLD"]), within=np.nan, composition=np.nan, asia_change=float(ji.loc[h1, "ASIA"] - ji.loc[h0, "ASIA"])))
    pd.DataFrame(rob).round(4).to_csv(R / "robustness.csv", index=False)
    main["corr_level"] = lv; main["corr_lag"] = lagc
    json.dump({k: (round(v, 4) if isinstance(v, float) else v) for k, v in main.items()}, open(R / "main.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(main, ensure_ascii=False, indent=0)); print(pd.read_csv(R / "robustness.csv").to_string())
    print(core.OTHER.describe())


if __name__ == "__main__":
    main()
