"""05 図：figures/ に6枚。図6は reports/ の HTML を playwright で画像にする。"""
import json, pathlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

ROOT = pathlib.Path(__file__).resolve().parents[1]
RES, FIG = ROOT / "results", ROOT / "figures"
FIG.mkdir(exist_ok=True)
for f in fm.findSystemFonts():
    if "NotoSansCJK" in f or "NotoSansJP" in f:
        fm.fontManager.addfont(f)
plt.rcParams["font.family"] = ["Noto Sans CJK JP", "Noto Sans JP", "sans-serif"]
plt.rcParams["axes.spines.top"] = False; plt.rcParams["axes.spines.right"] = False
J = json.load(open(RES / "main.json"))
NOTE = "架空の会社「サンプルマート（架空）」の合成データ。実在の会社とは関係がない"
C1, C2, C3, CG = "#2563a8", "#d9822b", "#3a9a5b", "#8a8a8a"


def months(a, b):
    return [p.strftime("%Y-%m") for p in pd.period_range(a, b, freq="M")]


def save(fig, name):
    fig.text(0.01, -0.03, NOTE, fontsize=8, color=CG)
    fig.savefig(FIG / name, dpi=150, bbox_inches="tight"); plt.close(fig)


# 図1：全社（FY2026 に営業する22店）の月の売上と、FY2026 の予算（基本と80%の幅）、4〜8月の実績
m = pd.read_csv(ROOT / "data" / "store_month_seeds.csv.gz"); m = m[m.seed == 0]
FY26 = sorted(set(range(1, 25)) - {21, 24})
act = m[m.store_id.isin(FY26)].groupby("ym").sales.sum() / 1e8
b = pd.read_csv(RES / "D_budget_store_month_base.csv").groupby("ym").sales.sum() / 1e8
lo, hi = J["D_budget"]["range80_pct"]
fig, ax = plt.subplots(figsize=(10, 4.6))
h = act.loc[:"2026-03"]
x = {ym: i for i, ym in enumerate(months("2022-04", "2027-03"))}
ax.plot([x[i] for i in h.index], h.values, color=CG, lw=1.6, label="実績（FY2022〜FY2025）")
xb = [x[i] for i in b.index]
ax.fill_between(xb, b.values * (1 + lo / 100), b.values * (1 + hi / 100), color=C1, alpha=0.18, label=f"予算の幅（80%、1年合計の幅 {lo:+.1f}〜{hi:+.1f}% を各月に当てた）")
ax.plot(xb, b.values, color=C1, lw=2.2, label="予算（基本）")
e = act.loc["2026-04":"2026-08"]
ax.plot([x[i] for i in e.index], e.values, "o", color=C2, ms=6, label="FY2026 の実績（4〜8月、答え合わせ）")
ticks = [ym for ym in x if ym.endswith("-04")]
ax.set_xticks([x[t] for t in ticks]); ax.set_xticklabels([f"FY{t[:4]}" for t in ticks])
ax.axvline(x["2026-03"] + 0.5, color=CG, ls=":", lw=1)
ax.set_ylabel("月の売上（億円）"); ax.legend(fontsize=8.5, loc="upper left", frameon=False)
ax.set_title("FY2026 の予算：22店の売上、基本と80%の幅。4〜8月の実績は5か月中4か月で予算を下回った", fontsize=12, loc="left")
save(fig, "fig1_budget_fan.png")

# 図2：自社のバックテスト：1年分の合計の外れ（MAPE）、単位ごと
s1 = pd.read_csv(RES / "A_annual_mape_by_level.csv")
order = [("店", "直接"), ("地域", "直接"), ("地域", "足し上げ"), ("全社", "直接"), ("全社", "足し上げ")]
models = ["季節ナイーブ", "季節ナイーブ＋伸び", "季節ナイーブ＋伸び＋暦", "ETS", "SARIMA"]
cols = [CG, C1, "#1b3f6b", C3, C2]
fig, ax = plt.subplots(figsize=(10, 4.4))
w = 0.16
for k, (mdl, c) in enumerate(zip(models, cols)):
    v = [float(s1[(s1.level == a) & (s1.method == b_)][mdl].iloc[0]) for a, b_ in order]
    ax.bar(np.arange(len(order)) + (k - 2) * w, v, w, color=c, label=mdl)
    for i, vv in enumerate(v):
        ax.text(i + (k - 2) * w, vv + 0.05, f"{vv:.1f}", ha="center", fontsize=7)
ax.set_xticks(range(len(order))); ax.set_xticklabels([f"{a}（{b_}）" for a, b_ in order])
ax.set_ylabel("1年分の合計の外れ（MAPE、%）"); ax.legend(fontsize=8, ncol=5, frameon=False, loc="upper right")
ax.set_title("自社の過去で試す：1年分の合計の外れ（起点13回 × 乱数の種20通り、20店）", fontsize=12, loc="left")
save(fig, "fig2_backtest_annual_mape.png")

# 図3：幅の作り方ごとの、覆えた割合（自社）
cs = pd.read_csv(RES / "C_interval_coverage_summary.csv")
pick = [("①モデルの区間", "ETS"), ("①モデルの区間", "SARIMA"), ("③'業界の外れだけ", "季節ナイーブ＋伸び＋暦"),
        ("③業界の外れ＋自社の揺れ", "季節ナイーブ＋伸び＋暦"), ("③業界の外れ＋自社の揺れ", "季節ナイーブ＋伸び")]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
lab, cov, wid = [], [], []
for mt, md in pick:
    r = cs[(cs.method == mt) & (cs.model == md)]
    if len(r):
        lab.append(f"{mt}\n（{md}）"); cov.append(float(r.covered.iloc[0])); wid.append(float(r.width.iloc[0]))
yy = np.arange(len(lab))[::-1]
a1.barh(yy, cov, color=[C2, C2, C1, "#1b3f6b", "#1b3f6b"][:len(lab)])
a1.axvline(80, color="k", ls="--", lw=1); a1.text(80.5, yy[-1] - 0.45, "目標 80%", fontsize=8)
for y_, v in zip(yy, cov):
    a1.text(v + 1, y_, f"{v:.0f}%", va="center", fontsize=9)
a1.set_yticks(yy); a1.set_yticklabels(lab, fontsize=8); a1.set_xlim(0, 110); a1.set_xlabel("実際が幅に入った割合（%）")
a1.set_title("覆えた割合（自社、起点13回×20通り）", fontsize=11, loc="left")
a2.barh(yy, wid, color=[C2, C2, C1, "#1b3f6b", "#1b3f6b"][:len(lab)])
for y_, v in zip(yy, wid):
    a2.text(v + 0.1, y_, f"{v:.1f}%", va="center", fontsize=9)
a2.set_yticks(yy); a2.set_yticklabels([]); a2.set_xlabel("幅の広さ（1年合計の上下の差、%、中央値）")
a2.set_title("幅の広さ", fontsize=11, loc="left")
fig.suptitle("幅の作り方を比べる：モデルの区間は狭すぎ、業界の外れを借りると目標に近づく", fontsize=12, x=0.01, ha="left")
save(fig, "fig3_interval_coverage.png")

# 図4：業界（スーパー）の1年合計の外れの推移（季節ナイーブ＋伸び）
ib = pd.read_csv(RES / "B_industry_backtest_h12.csv")
d = ib[ib.model == "季節ナイーブ＋伸び"].copy()
fig, ax = plt.subplots(figsize=(10, 4.2))
dd = d.copy(); dd["x"] = pd.to_datetime(dd.target_end)
ax.plot(dd.x, dd.log_err * 100, color=C1, lw=1.4)
cv = dd[dd.covid]
ax.scatter(cv.x, cv.log_err * 100, s=8, color=CG, zorder=3, label="コロナ期の月を含む（幅の計算から外した）")
ax.axhline(0, color="k", lw=0.8)
nc = dd[~dd.covid & (dd.target_end <= "2026-03")]
q10, q90 = np.quantile(nc.log_err * 100, [0.1, 0.9])
ax.axhspan(q10, q90, color=C1, alpha=0.12, label=f"外れの80%の範囲（{q10:+.1f}〜{q90:+.1f}%、2026-03 までに結果が出た回）")
ax.set_ylabel("実際 ÷ 予測 − 1（%、対数）"); ax.set_xlabel("予測した1年の最後の月")
ax.legend(fontsize=8.5, frameon=False, loc="lower left")
ax.set_title("業界（商業動態統計・スーパー）で同じ作り方をすると、1年合計はこれだけ外れる", fontsize=12, loc="left")
save(fig, "fig4_industry_errors.png")

# 図5：売上の幅が、利益ではどれだけ広がるか
sc = pd.read_csv(RES / "D_budget_scenarios.csv", index_col=0) / 1e8
rows = ["FY2025 実績（同じ22店）", "下振れ（10%）", "基本", "上振れ（90%）"]
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
colr = [CG, C2, C1, C3]
for ax_, col, t in [(a1, "sales", "売上（億円）"), (a2, "operating_profit", "営業利益（億円）")]:
    v = sc.loc[rows, col].values
    ax_.bar(range(4), v, color=colr)
    for i, vv in enumerate(v):
        ax_.text(i, vv * 1.005, f"{vv:.1f}" if col == "sales" else f"{vv:.2f}", ha="center", fontsize=9)
    ax_.set_xticks(range(4)); ax_.set_xticklabels(["FY2025\n実績", "下振れ\n(10%)", "基本", "上振れ\n(90%)"])
    ax_.set_title(t, fontsize=11, loc="left")
    if col == "sales":
        ax_.set_ylim(v.min() * 0.95, v.max() * 1.02)
    else:
        ax_.set_ylim(0, v.max() * 1.2)
sp = (sc.loc["上振れ（90%）", "sales"] / sc.loc["基本", "sales"] - 1) * 100
op_lo, op_hi = J["D_op_range_pct_vs_base"]
fig.suptitle(f"売上の幅は基本の ±{sp:.1f}% ほどでも、営業利益では {op_lo:+.0f}〜{op_hi:+.0f}% に広がる（売上の縦軸は0からではない）", fontsize=12, x=0.01, ha="left")
save(fig, "fig5_sales_to_profit_range.png")

# 図6：1枚の予算案（HTML を画像に）
html = ROOT / "reports" / "budget_FY2026_onepage.html"
if html.exists():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 900, "height": 1200}, device_scale_factor=2)
        pg.goto(html.resolve().as_uri()); pg.wait_for_timeout(300)
        pg.screenshot(path=str(FIG / "fig6_budget_onepage.png"), full_page=True); br.close()
print("ok")
