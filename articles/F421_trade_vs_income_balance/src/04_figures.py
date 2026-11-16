"""04 図（PNG、日付などのメタデータは入れない）。"""
import json, pathlib
import numpy as np
import pandas as pd
from figstyle import plt, C, INK, INK2, GRID, save, style

ROOT = pathlib.Path(__file__).resolve().parent.parent
D, R, F = ROOT / "data", ROOT / "results", ROOT / "figures"
F.mkdir(exist_ok=True)
SRC = "出典：財務省・日本銀行「国際収支統計」、日本銀行「外国為替相場」（日本銀行 時系列統計データ検索サイト）をもとに作成者が加工して作成"
m = json.load(open(R / "main.json", encoding="utf-8"))
q = json.load(open(R / "requestion.json", encoding="utf-8"))
a = pd.read_csv(D / "annual.csv").set_index("year").drop(columns=["source"])
t = a / 1e4

# 図1 貿易収支と第一次所得収支
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(t.index, t.trade, color=C[0], lw=2.3, label="貿易収支（1996年〜）")
ax.plot(t.index, t.trade_services, color=C[0], lw=1.2, ls="--", label="貿易・サービス収支")
ax.plot(t.index, t.primary, color=C[1], lw=2.3, label="第一次所得収支")
ax.axhline(0, color=INK2, lw=0.8)
ax.axvline(m["first_year_primary_gt_trade"], color=GRID, lw=1)
ax.text(m["first_year_primary_gt_trade"] - 0.3, 33, f"{m['first_year_primary_gt_trade']}年\n所得収支が\n貿易収支を上回る", fontsize=8.6, color=INK2, ha="right")
ax.axvline(m["first_trade_deficit_year"], color=GRID, lw=1)
ax.text(m["first_trade_deficit_year"] + 0.3, 33, f"{m['first_trade_deficit_year']}年\n貿易収支が赤字に", fontsize=8.6, color=INK2)
ax.set_xlim(1984.5, 2025.5); ax.set_ylim(-26, 45)
ax.set_ylabel("兆円（暦年）")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"第一次所得収支は{m['first_year_primary_gt_trade']}年に貿易収支を上回り、その後一度も逆転していない", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.17)
save(fig, F / "fig1_trade_vs_primary.png", SRC, "注：1985〜95年は年次の組替の値で、貿易収支とサービス収支の内訳がないため貿易・サービス収支だけを示す。")

# 図2 経常収支の内訳
s = t.loc[1996:2025]
fig, ax = plt.subplots(figsize=(8.8, 5.0))
items = [("trade", "貿易収支", C[0]), ("services", "サービス収支", C[2]), ("primary", "第一次所得収支", C[1]), ("secondary", "第二次所得収支", C[5])]
pos = np.zeros(len(s)); neg = np.zeros(len(s))
for c, lab, col in items:
    v = s[c].values
    bottom = np.where(v >= 0, pos, neg)
    ax.bar(s.index, v, bottom=bottom, color=col, width=0.8, label=lab)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.plot(s.index, s.ca, color=INK, lw=1.8, marker="o", ms=3, label="経常収支")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("兆円（暦年）")
ax.legend(frameon=False, loc="upper left", fontsize=8.6, ncol=3)
ax.set_ylim(-25, 50)
style(ax)
ax.set_title(f"2025年は第一次所得収支{m['primary_2025']:.1f}兆円が、経常収支{m['ca_2025']:.1f}兆円より大きい", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig2_current_account.png", SRC)

# 図3 第一次所得収支の内訳
b = pd.read_csv(R / "primary_breakdown.csv").set_index("year")
parts = [("di_dividends", "直接投資：配当金等", C[1]), ("di_reinvested", "直接投資：再投資収益", "#f2a27f"), ("di_interest", "直接投資：利子", "#f7cdb7"),
         ("pf_dividends", "証券投資：配当金", C[0]), ("pf_bond_interest", "証券投資：債券利子", "#8db8ea"),
         ("other_invest_income", "その他投資収益", C[2]), ("comp_employees", "雇用者報酬など", C[5])]
b["comp_employees"] = b.comp_employees + b.other_primary
fig, ax = plt.subplots(figsize=(8.8, 5.0))
pos = np.zeros(len(b)); neg = np.zeros(len(b))
for c, lab, col in parts:
    v = b[c].values
    bottom = np.where(v >= 0, pos, neg)
    ax.bar(b.index, v, bottom=bottom, color=col, width=0.8, label=lab)
    pos += np.where(v >= 0, v, 0); neg += np.where(v < 0, v, 0)
ax.axhline(0, color=INK2, lw=0.8)
ax.set_ylabel("兆円（暦年、ネット）")
ax.legend(frameon=False, loc="upper left", fontsize=8.4, ncol=2)
style(ax)
ax.set_title(f"直接投資の収益が{m['first_year_di_gt_pf']}年から証券投資の収益を上回り、2025年は{m['di_share_primary_2025']:.0f}%", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.97, top=0.91, bottom=0.14)
save(fig, F / "fig3_primary_breakdown.png", SRC)

# 図4 円とドル建て（2005年＝100）
idx_y = a.loc[2005:2025, "primary"] / a.loc[2005, "primary"] * 100
idx_u = a.loc[2005:2025, "primary_usd"] / a.loc[2005, "primary_usd"] * 100
fig, ax = plt.subplots(figsize=(8.8, 5.0))
ax.plot(idx_y.index, idx_y, color=C[1], lw=2.3, label="円で見た第一次所得収支")
ax.plot(idx_u.index, idx_u, color=C[0], lw=2.3, label="ドルで見た第一次所得収支")
ax.text(2025.2, idx_y.iloc[-1], f"{idx_y.iloc[-1]:.0f}", fontsize=9, color=C[1], va="center")
ax.text(2025.2, idx_u.iloc[-1], f"{idx_u.iloc[-1]:.0f}", fontsize=9, color=C[0], va="center")
ax.set_xlim(2004.5, 2026.5); ax.set_xticks(range(2005, 2026, 5))
ax.set_ylabel("2005年＝100")
ax.legend(frameon=False, loc="upper left", fontsize=9)
style(ax)
ax.set_title(f"2012→25年の円での伸びの{q['fx_share_of_log_growth_2012_pct']:.0f}%は円安の分（ドルでは+{q['primary_usd_growth_2012_pct']:.0f}%）", loc="left", fontsize=12)
fig.subplots_adjust(left=0.08, right=0.95, top=0.91, bottom=0.17)
save(fig, F / "fig4_yen_vs_usd.png", SRC, f"注：ドル建ては月ごとの値をその月のドル円（月中平均）で割って合計。ドル円は2005年{q['usdjpy_2005']:.1f}円、2012年{q['usdjpy_2012']:.1f}円、2025年{q['usdjpy_2025']:.1f}円。")
