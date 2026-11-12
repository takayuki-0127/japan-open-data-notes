"""299 築年数の古い家は、どれだけ増えたのか（住宅・土地統計調査 時系列 第20-1表：持ち家、2003〜2023年）

- 調査年ごとの「建築の時期」別の持ち家数（全国）
- 同じ築年数の目安で比べる：築43年以上 = 2003年の調査では1960年以前、2013年は1970年以前、2023年は1980年以前
- 同じ建築時期の持ち家が、20年でどれだけ残っているか（2003 → 2023年の調査）
- 1980年以前に建った持ち家のうち、直近の約5年に耐震改修工事をした割合
"""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from common import load, rows, num, year_from_label, save_json, savefig, setup_font, DATA

setup_font()
D = load()

def period(eng):
    """英語の建築時期ラベル → (始まりの年, 終わりの年)。'1960 or earlier' は (None, 1960)"""
    e = eng.replace("～", "~").replace("Sep.", "").strip()
    m = re.match(r"(\d{4}) or earlier", e)
    if m: return (None, int(m.group(1)))
    m = re.match(r"(\d{4})\s*(?:~|to)\s*(\d{4})", e)
    if m: return (int(m.group(1)), int(m.group(2)))
    return None

recs = []
for k in sorted(x for x in D if x.startswith("t052__")):
    R = rows(D[k]); y = None
    for r in R:
        yy = year_from_label(r[1]) if r[1].startswith("その") else None
        if yy: y = yy
    struct = None; started = False
    for r in R:
        lab = r[1].replace("　", "").replace(" ", "")
        p0 = period(r[2])
        if lab.startswith("持ち家総数"):
            struct = "総数"; started = True
        elif started and p0 is None and num(r[4]) is not None:
            if lab.startswith("防火木造"): struct = "防火木造"
            elif lab.startswith("木造"): struct = "木造"
            elif lab.startswith("非木造"): struct = "非木造"
            elif lab.startswith("その他"): struct = "その他"
            else: struct = "?" + lab
        if not started: continue
        if lab.startswith("一戸建") or lab.startswith("長屋建") or lab.startswith("共同住宅"):
            break
        tot, ren = num(r[4]), num(r[5])
        p = period(r[2])
        if tot is None: continue
        recs.append(dict(survey=y, struct=struct, label=lab, start=p[0] if p else None, end=p[1] if p else None,
                         is_total=p is None, owned=tot, renovated=ren))
df = pd.DataFrame(recs)
df.to_csv(os.path.join(DATA, "owned_by_construction_period.csv"), index=False)

tot = df[(df.struct == "総数") & df.is_total].set_index("survey").owned
P = df[(df.struct == "総数") & ~df.is_total]
known = P.groupby("survey").owned.sum()
unknown_share = ((tot - known) / tot * 100).round(2)

def built_by(survey, last_year, struct="総数"):
    s = df[(df.survey == survey) & (df.struct == struct) & ~df.is_total]
    assert (s.end <= last_year).sum() > 0
    part = s[s.end <= last_year]
    # 区切りがまたがっていないことを確認
    assert not ((s.start.fillna(0) <= last_year) & (s.end > last_year)).any(), (survey, last_year)
    return float(part.owned.sum()), float(part.renovated.sum())

# 築43年以上（各調査で、調査年 − 43 年以前に建ったもの）
age43 = {}
for sv, cut in [(2003, 1960), (2013, 1970), (2023, 1980)]:
    n, _ = built_by(sv, cut)
    age43[sv] = dict(cut=cut, owned=n, share_known=round(n / known[sv] * 100, 1), share_total=round(n / tot[sv] * 100, 1))
# 1980年以前（旧耐震基準のころ）の持ち家
pre81 = {}
for sv in sorted(df.survey.unique()):
    n, rv = built_by(sv, 1980)
    pre81[int(sv)] = dict(owned=n, share_known=round(n / known[sv] * 100, 1), renovated=rv, renov_rate=round(rv / n * 100, 2))
# 同じ建築時期が残っている割合（2003 → 2023）
surv = {}
for (a, b) in [(None, 1970), (1971, 1980), (1981, 1990)]:
    def cnt(sv):
        s = df[(df.survey == sv) & (df.struct == "総数") & ~df.is_total]
        lo = a if a else 0
        return float(s[(s.start.fillna(0) >= lo) & (s.end <= b)].owned.sum())
    surv[f"{a or ''}〜{b}"] = {int(sv): cnt(sv) for sv in [2003, 2008, 2013, 2018, 2023]}
surv_ratio = {k: round(v[2023] / v[2003] * 100, 1) for k, v in surv.items()}
# 木造の割合（1980年以前・2023年）
w80, _ = built_by(2023, 1980, "木造"); n80, _ = built_by(2023, 1980)
wall, _ = (float(df[(df.survey == 2023) & (df.struct == "木造") & df.is_total].owned.iloc[0]), 0)

out = dict(
    total_owned={int(k): v for k, v in tot.items()}, unknown_period_share_pct={int(k): v for k, v in unknown_share.items()},
    age43=age43, pre1980=pre81, survival_2003_2023=surv, survival_ratio_pct=surv_ratio,
    wooden_share_pre1980_2023=round(w80 / n80 * 100, 1), wooden_share_all_2023=round(wall / tot[2023] * 100, 1),
)
save_json("a299_main.json", out)

# --- 図 ---
fig, ax = plt.subplots(figsize=(7.2, 4.2))
xs = [f"2003年調査\n（1960年以前）", f"2013年調査\n（1970年以前）", f"2023年調査\n（1980年以前）"]
vs = [age43[s]["share_known"] for s in (2003, 2013, 2023)]
ns = [age43[s]["owned"] / 1e4 for s in (2003, 2013, 2023)]
ax.bar(xs, vs, color=["#9ecae1", "#4292c6", "#08519c"], width=0.55)
for i, (v, n) in enumerate(zip(vs, ns)):
    ax.text(i, v + 0.6, f"{v:.1f}%\n（{n:,.0f}万戸）", ha="center", fontsize=9.5)
ax.set_ylabel("持ち家（建築時期が分かるもの）に占める割合（%）"); ax.set_ylim(0, 32)
ax.set_title("建ってから43年以上の持ち家は、20年で1割から4分の1に", fontsize=10.5)
savefig(fig, "a299_age43.png")

fig, ax = plt.subplots(figsize=(7.2, 4.2))
for (k, v), c in zip(surv.items(), ["#7f7f7f", "#d62728", "#1f77b4"]):
    ys = [v[s] / v[2003] * 100 for s in [2003, 2008, 2013, 2018, 2023]]
    lab = {"〜1970": "1970年以前に建った持ち家", "1971〜1980": "1971〜80年に建った持ち家", "1981〜1990": "1981〜90年に建った持ち家"}[k]
    ax.plot([2003, 2008, 2013, 2018, 2023], ys, marker="o", lw=2, color=c, label=lab)
    dy = {"1971〜1980": -1.4, "1981〜1990": 1.4}.get(k, 0)
    ax.text(2023.6, ys[-1] + dy, f"{ys[-1]:.0f}", color=c, va="center", fontsize=9)
ax.set_ylim(40, 105); ax.set_xlim(2001, 2026)
ax.set_ylabel("2003年調査の戸数を100とした値"); ax.set_xticks([2003, 2008, 2013, 2018, 2023])
ax.legend(frameon=False, fontsize=9, loc="lower left")
ax.set_title("1971〜80年・1981〜90年に建った持ち家は、20年で8割が残っていた", fontsize=10.5)
savefig(fig, "a299_survival.png")

fig, ax = plt.subplots(figsize=(7.4, 4.2))
s23 = df[(df.survey == 2023) & ~df.is_total & df.struct.isin(["木造", "非木造"])].copy()
s23["lab"] = s23.apply(lambda r: (f"{int(r.start)}〜" if not np.isnan(r.start) else "〜") + f"{int(r.end)}", axis=1)
order = s23[s23.struct == "木造"].lab.tolist()
wv = s23[s23.struct == "木造"].set_index("lab").owned.reindex(order) / 1e4
nv = s23[s23.struct == "非木造"].set_index("lab").owned.reindex(order) / 1e4
ax.bar(order, wv, color="#a6761d", label="木造")
ax.bar(order, nv, bottom=wv, color="#7570b3", label="非木造")
ax.set_ylabel("2023年の持ち家数（万戸）"); ax.legend(frameon=False, fontsize=9)
ax.set_xlabel("建築の時期（年）。区分の長さは10年・5年・約3年（2021〜2023年9月）と違う"); plt.setp(ax.get_xticklabels(), fontsize=8.5, rotation=30, ha="right")
ax.set_title("いまの持ち家のうち、1980年以前に建ったものは820万戸", fontsize=10.5)
savefig(fig, "a299_by_period_2023.png")
