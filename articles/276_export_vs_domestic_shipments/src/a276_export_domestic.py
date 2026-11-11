"""276 出荷のうち、輸出向けはどれだけ増えたのか（鉱工業出荷内訳表）"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font, splice

setup_font()
cur = pd.read_csv(DATA / "shipments_breakdown_2018_2026.csv", dtype={"code": str})
old = pd.read_csv(DATA / "shipments_breakdown_connected_1998_2022.csv", dtype={"code": str})
w = pd.read_csv(DATA / "weights_2020.csv", dtype={"code": str}).set_index("code")
name = cur.drop_duplicates("code").set_index("code").name


def series(code, kind):
    a = pd.to_numeric(old[(old.code == code) & (old.kind == kind)].set_index("ym").value, errors="coerce")
    b = cur[(cur.code == code) & (cur.kind == kind)].set_index("ym").value
    j = a.dropna().index.intersection(b.index)
    return splice(a, b), (float((a[j] - b[j]).abs().max()) if len(j) else None)


def annual(s):
    s = s[s.index <= pd.Period("2025-12", "M")]
    return s.groupby(s.index.year).mean()


rows = []; gaps = {}
for c in name.index:
    if c not in w.index: continue
    E, ge = series(c, "exp_sa"); D, gd = series(c, "dom_sa"); S, gs = series(c, "ship_sa"); gaps[c] = (ge, gd, gs)
    E, D, S = annual(E), annual(D), annual(S)
    we, wd, ws = [float(x) for x in w.loc[c, ["w_exp", "w_dom", "w_ship"]]]
    share = we * E / (we * E + wd * D) * 100
    y0 = int(E.dropna().index.min())
    rows.append({"code": c, "name": name[c], "first_year": y0, "w_exp_share_2020": round(we / ws * 100, 1),
                 "exp_first": round(E[y0], 1), "exp_2007": round(E.get(2007, np.nan), 1), "exp_2019": round(E[2019], 1), "exp_2025": round(E[2025], 1),
                 "dom_first": round(D[y0], 1), "dom_2007": round(D.get(2007, np.nan), 1), "dom_2019": round(D[2019], 1), "dom_2025": round(D[2025], 1),
                 "share_first": round(share[y0], 1), "share_2007": round(share.get(2007, np.nan), 1), "share_2025": round(share[2025], 1),
                 "contrib_exp_pt": round(we / ws * (E[2025] - E[y0]), 1), "contrib_dom_pt": round(wd / ws * (D[2025] - D[y0]), 1),
                 "ship_change_pt": round(S[2025] - S[y0], 1), "check_resid_2025": round(float(S[2025] - (we * E[2025] + wd * D[2025]) / ws), 2)})
    if c == "1000000000":
        tot = pd.DataFrame({"exp": E, "dom": D, "ship": S, "exp_share_pct": share}).round(2); tot.to_csv(RES / "a276_total_annual.csv")
t = pd.DataFrame(rows).set_index("code"); t.to_csv(RES / "a276_by_industry.csv")
IND = [c for c in t.index if c.startswith("11") and c != "1100000000" and c != "1110000000"]
r = t.loc["1000000000"]
# 頑健性：月次の原指数で見ても同じか（2018年以降）、2019年を起点にすると
cur["y"] = cur.ym // 100
yn = cur[(cur.code == "1000000000") & (cur.y <= 2025)].groupby(["kind", "y"]).value.mean()
main = {"total": r.to_dict(), "gaps_overlap_2018_2022": gaps, "n_ind": len(IND),
        "n_share_up": int((t.loc[IND].share_2025 > t.loc[IND].share_first).sum()),
        "n_exp_up": int((t.loc[IND].exp_2025 > t.loc[IND].exp_first).sum()), "n_dom_down": int((t.loc[IND].dom_2025 < t.loc[IND].dom_first).sum()),
        "since2019": {"exp_pct": round((r.exp_2025 / r.exp_2019 - 1) * 100, 1), "dom_pct": round((r.dom_2025 / r.dom_2019 - 1) * 100, 1)},
        "since2007": {"exp_pct": round((r.exp_2025 / r.exp_2007 - 1) * 100, 1), "dom_pct": round((r.dom_2025 / r.dom_2007 - 1) * 100, 1)},
        "max_abs_resid": round(float(t.check_resid_2025.abs().max()), 2)}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1, default=float)

tot = pd.read_csv(RES / "a276_total_annual.csv", index_col=0)
# 図1：輸出向けと国内向け
fig, ax = plt.subplots(figsize=(8.5, 4.4))
ax.plot(tot.index, tot.exp, color="#d1495b", lw=2, marker="o", ms=3, label="輸出向け")
ax.plot(tot.index, tot.dom, color="#2e86ab", lw=2, marker="o", ms=3, label="国内向け")
ax.plot(tot.index, tot.ship, color="#333", lw=1.2, ls="--", label="出荷全体")
for y in [1998, 2007, 2025]:
    ax.annotate(f"{tot.exp[y]:.0f}", (y, tot.exp[y]), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8, color="#d1495b")
    ax.annotate(f"{tot.dom[y]:.0f}", (y, tot.dom[y]), textcoords="offset points", xytext=(0, -13), ha="center", fontsize=8, color="#2e86ab")
ax.set_ylabel("出荷指数（季節調整済の年平均、2020年=100）"); ax.legend(frameon=False, fontsize=9)
ax.set_title("鉱工業の出荷：輸出向けは1998年の1.5倍、国内向けは2割減（1998〜2025年）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a276_exp_dom.png", dpi=150); plt.close()

# 図2：輸出向けの割合（2020年の価格で）
fig, ax = plt.subplots(figsize=(8, 3.8))
ax.plot(tot.index, tot.exp_share_pct, color="#d1495b", lw=2, marker="o", ms=3)
for y in [1998, 2007, 2009, 2025]:
    ax.annotate(f"{tot.exp_share_pct[y]:.1f}%", (y, tot.exp_share_pct[y]), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8)
ax.set_ylabel("出荷に占める輸出向けの割合（%）"); ax.set_ylim(0, tot.exp_share_pct.max() * 1.25)
ax.set_title("出荷に占める輸出向けの割合（2020年のウエイトで重みづけ）", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a276_share.png", dpi=150); plt.close()

# 図3：業種別の輸出向けの割合（最初の年→2025年）
ti = t.loc[IND].sort_values("share_2025")
short = lambda s: s.replace("工業", "").replace("・紙加工品", "")
fig, ax = plt.subplots(figsize=(8.5, 5.6))
yy = np.arange(len(ti))
for i, (a, b) in enumerate(zip(ti.share_first, ti.share_2025)):
    ax.annotate("", xy=(b, i), xytext=(a, i), arrowprops=dict(arrowstyle="->", color="#d1495b" if b > a else "#2e86ab", lw=1.5))
ax.scatter(ti.share_first, yy, color="#999", s=14, zorder=3, label="最初の年")
ax.scatter(ti.share_2025, yy, color="#333", s=18, zorder=3, label="2025年")
ax.set_yticks(yy); ax.set_yticklabels([f"{short(n)}（{y}年〜）" for n, y in zip(ti.name, ti.first_year)], fontsize=8)
ax.set_xlabel("出荷に占める輸出向けの割合（%）"); ax.legend(frameon=False, fontsize=8, loc="lower right")
ax.set_title("業種別の輸出向けの割合：最初の年→2025年", fontsize=11)
fig.tight_layout(); fig.savefig(FIG / "a276_by_industry.png", dpi=150); plt.close()
print(t[["name", "first_year", "w_exp_share_2020", "exp_first", "exp_2025", "dom_first", "dom_2025", "share_first", "share_2025", "contrib_exp_pt", "contrib_dom_pt", "ship_change_pt", "check_resid_2025"]].to_string())
print({k: v for k, v in main.items() if k not in ("total", "gaps_overlap_2018_2022")}, main["gaps_overlap_2018_2022"]["1000000000"])
