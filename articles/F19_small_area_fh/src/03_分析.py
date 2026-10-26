"""大腸がん検診（国保の被保険者、40〜69歳）の受診率を Fay–Herriot モデルで縮小推定する。
主な年は2023年度。2024年度の直接推定値を「答え」として、どちらの推定値が翌年をよく当てるかを確かめる。
"""
import json
import numpy as np, pandas as pd
from common import DATA, RES
from fh import fit

d = pd.read_csv(DATA / "screening_long.csv")
d = d[(d.n_colon > 0) & d.y_colon.notna() & d["pop"].notna() & (d["pop"] > 0)].copy()
d["p"] = d.y_colon / d.n_colon
d["z"] = np.arcsin(np.sqrt(d.p))           # 角変換：分散 ≒ 1/(4n) で p によらない
d["Dz"] = 1 / (4 * d.n_colon)
COV = ["aged", "logdens", "clinic", "hosp", "primary", "single"]
for c in COV:
    m, s = d[c].mean(), d[c].std()
    d[c + "_s"] = (d[c] - m) / s
back = lambda z: np.sin(np.clip(z, 0, np.pi / 2)) ** 2


def design(g, kind):
    X = [np.ones(len(g))]
    if kind in ("cov", "cov_pref"):
        X += [g[c + "_s"].values for c in COV]
    if kind in ("pref", "cov_pref"):
        P = pd.get_dummies(g.pref, drop_first=True).astype(float).values
        X += list(P.T)
    return np.column_stack(X)


def run(year, kind="cov_pref", phi=1.0, data=None):
    g = (d if data is None else data)
    g = g[g.year == year].copy()
    r = fit(g.z.values, design(g, kind), phi * g.Dz.values)
    g["eb_z"] = r["eb"]; g["gamma"] = r["gamma"]; g["synth_z"] = r["synth"]
    g["eb"] = back(g.eb_z); g["synth"] = back(g.synth_z)
    g["se_eb"] = np.sqrt(r["mse"]) * np.abs(np.sin(2 * g.eb_z))   # デルタ法で率の尺度へ
    g["se_dir"] = np.sqrt(g.p * (1 - g.p) / g.n_colon)
    return g, r


def validate(g, nxt):
    m = g.merge(nxt[["code", "p"]].rename(columns={"p": "p_next"}), on="code")
    out = {}
    for lab, cond in SIZE.items():
        mm = m[cond(m.n_colon)]
        out[lab] = dict(n=len(mm),
                        mse_dir=float(np.mean((mm.p - mm.p_next) ** 2)),
                        mse_eb=float(np.mean((mm.eb - mm.p_next) ** 2)))
    return out


SIZE = {"全体": lambda n: n > 0, "500人未満": lambda n: n < 500, "500〜2,000人": lambda n: (n >= 500) & (n < 2000),
        "2,000〜1万人": lambda n: (n >= 2000) & (n < 10000), "1万人以上": lambda n: n >= 10000}

summary = {}
# --- 年をまたぐぶれから、二項分布以上のぶれ（過分散）の大きさを見積もる
w = d.pivot_table(index="code", columns="year", values="z")
wn = d.pivot_table(index="code", columns="year", values="n_colon")
ratios = []
for a, b in [(2021, 2022), (2022, 2023), (2023, 2024)]:
    diff2 = (w[b] - w[a]) ** 2
    exp2 = 1 / (4 * wn[a]) + 1 / (4 * wn[b])
    ok = diff2.notna() & exp2.notna()
    big = wn[a] >= 0
    ratios.append(float(np.median(diff2[ok] / exp2[ok]) / 0.4549))   # χ²(1) の中央値で割る
summary["overdispersion_phi_yearpairs"] = ratios
phi_hat = float(np.median(ratios))
summary["phi_hat"] = phi_hat

# --- 基本の推定（2023年度、共変量＋都道府県ダミー、二項分布どおりの分散）
g23, r23 = run(2023)
g24, _ = run(2024)
summary["base"] = dict(n=len(g23), A_z=r23["A"], sd_between_pt=float(np.sqrt(r23["A"]) * 100 * 2 * np.sqrt(0.2 * 0.8)),
                       gamma_median=float(np.median(r23["gamma"])),
                       gamma_by_size={k: float(g23.loc[f(g23.n_colon), "gamma"].median()) for k, f in SIZE.items()},
                       beta=dict(zip(["const"] + COV, map(float, r23["beta"][:7]))),
                       validation_2024=validate(g23, g24))
g23.to_csv(RES / "estimates_2023.csv", index=False,
           columns=["code", "name", "pref", "n_colon", "y_colon", "p", "se_dir", "eb", "se_eb", "synth", "gamma"])

# --- 過分散を入れた版（年ごとのぶれの実測から D を φ 倍）
g23o, r23o = run(2023, phi=phi_hat)
summary["overdisp"] = dict(phi=phi_hat, gamma_by_size={k: float(g23o.loc[f(g23o.n_colon), "gamma"].median()) for k, f in SIZE.items()},
                           validation_2024=validate(g23o, g24))
g23o[["code", "eb", "gamma"]].rename(columns={"eb": "eb_od", "gamma": "gamma_od"}).to_csv(RES / "estimates_2023_overdisp.csv", index=False)

# --- ランキング：上位・下位50の中の小さな町
def rank_share(g, col, k=50):
    s = g.sort_values(col)
    lo, hi = s.head(k), s.tail(k)
    small = lambda x: int((x.n_colon < 500).sum())
    return dict(bottom_small=small(lo), top_small=small(hi), bottom_med_n=float(lo.n_colon.median()), top_med_n=float(hi.n_colon.median()))
summary["ranking"] = {"直接推定": rank_share(g23, "p"), "縮小推定": rank_share(g23, "eb"), "縮小推定（過分散あり）": rank_share(g23.assign(eb=g23o.eb.values), "eb"),
                      "全体での500人未満の割合": float((g23.n_colon < 500).mean())}
s_dir = g23.p.rank(ascending=False); s_eb = g23.eb.rank(ascending=False)
summary["ranking"]["top50_overlap"] = int(len(set(g23.code[s_dir <= 50]) & set(g23.code[s_eb <= 50])))
summary["ranking"]["bottom50_overlap"] = int(len(set(g23.code[s_dir > len(g23) - 50]) & set(g23.code[s_eb > len(g23) - 50])))

# --- 頑健性
rob = []
for lab, kw in [("基本（共変量＋都道府県）", {}), ("共変量なし（全国平均へ寄せる）", dict(kind="none")),
                ("都道府県ダミーだけ", dict(kind="pref")), ("共変量だけ", dict(kind="cov")),
                ("過分散あり（D×φ）", dict(phi=phi_hat))]:
    a, _ = run(2023, **kw); b, _ = run(2024, **kw)
    v = validate(a, b)
    rob.append(dict(設定=lab, 全体_直接=v["全体"]["mse_dir"], 全体_縮小=v["全体"]["mse_eb"],
                    小_直接=v["500人未満"]["mse_dir"], 小_縮小=v["500人未満"]["mse_eb"]))
# 2022→2023 でも同じ確かめ
a, _ = run(2022); b, _ = run(2023); v = validate(a, b)
rob.append(dict(設定="基本、2022→2023で検証", 全体_直接=v["全体"]["mse_dir"], 全体_縮小=v["全体"]["mse_eb"],
                小_直接=v["500人未満"]["mse_dir"], 小_縮小=v["500人未満"]["mse_eb"]))
# 受診者0の町を除く
dd = d[d.y_colon > 0]
a, _ = run(2023, data=dd); b, _ = run(2024, data=dd); v = validate(a, b)
rob.append(dict(設定="受診者0の町を除く", 全体_直接=v["全体"]["mse_dir"], 全体_縮小=v["全体"]["mse_eb"],
                小_直接=v["500人未満"]["mse_dir"], 小_縮小=v["500人未満"]["mse_eb"]))
# 都道府県ごとに別々に推定（町が20以上の県）
parts = []
for p_, gp in d[d.year == 2023].groupby("pref"):
    if len(gp) < 20:
        continue
    r = fit(gp.z.values, np.column_stack([np.ones(len(gp))] + [gp[c + "_s"].values for c in COV]), gp.Dz.values)
    parts.append(gp.assign(eb=back(r["eb"])))
gp23 = pd.concat(parts)
cmp_ = gp23.merge(g23[["code", "eb"]].rename(columns={"eb": "eb_nat"}), on="code")
summary["pref_separate"] = dict(n_pref=len(parts), n=len(cmp_), corr_with_national=float(np.corrcoef(cmp_.eb, cmp_.eb_nat)[0, 1]),
                                max_abs_diff_pt=float((cmp_.eb - cmp_.eb_nat).abs().max() * 100))
v = validate(gp23, g24)
rob.append(dict(設定="都道府県ごとに別々に推定", 全体_直接=v["全体"]["mse_dir"], 全体_縮小=v["全体"]["mse_eb"],
                小_直接=v["500人未満"]["mse_dir"], 小_縮小=v["500人未満"]["mse_eb"]))
rob = pd.DataFrame(rob)
for c in ["全体", "小"]:
    rob[c + "_改善%"] = (1 - rob[c + "_縮小"] / rob[c + "_直接"]) * 100
rob.to_csv(RES / "robustness.csv", index=False)
summary["robustness"] = rob.round(6).to_dict(orient="records")
json.dump(summary, open(RES / "summary.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps({k: summary[k] for k in ["phi_hat", "base", "overdisp", "ranking", "pref_separate"]}, ensure_ascii=False, indent=1))
print(rob.round(5).to_string())
