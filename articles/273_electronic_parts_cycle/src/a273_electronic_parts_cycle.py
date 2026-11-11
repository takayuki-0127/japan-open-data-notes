"""273 電子部品・デバイスの生産の山と谷は、鉱工業全体・情報通信機械とどう重なったか"""
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from common import DATA, RES, FIG, setup_font, splice

setup_font()
d = pd.read_csv(DATA / "prod_sa_two_sources.csv", dtype={"code": str})
NAME = {"1000000000": "鉱工業", "1105000000": "電子部品・デバイス", "1106000000": "電気・情報通信機械", "1106200000": "情報通信機械"}


def get(code):
    a = d[(d.code == code) & (d.source == "connected_1978_2022")].set_index("ym").value
    b = d[(d.code == code) & (d.source == "2020base_2018_")].set_index("ym").value
    j = a.index.intersection(b.index)
    gap = float((a[j] - b[j]).abs().max())
    return splice(pd.to_numeric(a, errors="coerce"), b), gap


S = {}; gaps = {}
for k in NAME:
    S[k], gaps[k] = get(k)
ep, tot, ict = S["1105000000"], S["1000000000"], S["1106200000"]
start = ep.index.min()
tot = tot[tot.index >= start]; ict = ict[ict.index >= start]
yoy = {k: (np.log(S[k]).diff(12) * 100)[lambda s: s.index >= start] for k in S}

# 山と谷：3か月移動平均の前後15か月での最大・最小
def turning(s, w=15):
    m = s.rolling(3, center=True).mean()
    out = []
    for i in range(w, len(m) - w):
        win = m.iloc[i - w:i + w + 1]
        if m.iloc[i] == win.max():
            out.append((m.index[i], "山"))
        elif m.iloc[i] == win.min():
            out.append((m.index[i], "谷"))
    return out


tp = turning(ep)
pairs = [(tp[i][0], tp[i + 1][0]) for i in range(len(tp) - 1) if tp[i][1] == "山" and tp[i + 1][1] == "谷"]
falls = []
for p, t in pairs:
    falls.append({"peak": str(p), "trough": str(t), "months": (t - p).n,
                  "ep_fall_pct": round((ep[t] / ep[p] - 1) * 100, 1),
                  "total_fall_pct_same_months": round((tot[t] / tot[p] - 1) * 100, 1),
                  "total_min_in_window_pct": round((tot[p:t].min() / tot[p] - 1) * 100, 1)})
falls = pd.DataFrame(falls); falls.to_csv(RES / "a273_peak_trough_falls.csv", index=False)

# 前年同月比の相関（期間別）と、先行・遅行
periods = [("1999-01", "2007-12"), ("2008-01", "2015-12"), ("2016-01", "2026-09")]
corr = []
for a, b in periods:
    e = yoy["1105000000"][a:b]
    corr.append({"from": a, "to": b, "corr_total": round(e.corr(yoy["1000000000"][a:b]), 2),
                 "corr_ict": round(e.corr(yoy["1106200000"][a:b]), 2), "sd_ep": round(e.std(), 1), "sd_total": round(yoy["1000000000"][a:b].std(), 1)})
corr = pd.DataFrame(corr); corr.to_csv(RES / "a273_corr_by_period.csv", index=False)
lead = {L: round(yoy["1105000000"].corr(yoy["1000000000"].shift(-L)), 3) for L in range(-6, 7)}
# 頑健性：12か月の対数差ではなく、HPなしの3か月平均の前年比
y3 = {k: (np.log(S[k].rolling(3).mean()).diff(12) * 100)[lambda s: s.index >= start] for k in S}
corr3 = [round(y3["1105000000"][a:b].corr(y3["1000000000"][a:b]), 2) for a, b in periods]
corr3i = [round(y3["1105000000"][a:b].corr(y3["1106200000"][a:b]), 2) for a, b in periods]
# 頑健性：期間の切れ目を2014・2018年にずらす
alt = {}
for cut in ["2014-01", "2018-01"]:
    e = yoy["1105000000"][cut:]; alt[cut] = {"corr_total": round(e.corr(yoy["1000000000"][cut:]), 2), "corr_ict": round(e.corr(yoy["1106200000"][cut:]), 2)}

# 頑健性：2016年以降からコロナの時期（2020年3月〜2021年12月）を除く
_e = yoy["1105000000"]["2016-01":]; _m = ~((_e.index >= pd.Period("2020-03", "M")) & (_e.index <= pd.Period("2021-12", "M")))
alt["2016_excl_covid"] = {"corr_total": round(_e[_m].corr(yoy["1000000000"]["2016-01":][_m]), 2), "corr_ict": round(_e[_m].corr(yoy["1106200000"]["2016-01":][_m]), 2)}
lv = lambda s, y: round(float(s[str(y)].mean()), 1)
main = {
    "splice_overlap_max_abs_diff": gaps,
    "ep_start": str(start), "ep_end": str(ep.index.max()),
    "level": {"ep": {y: lv(ep, y) for y in [1998, 2000, 2007, 2019, 2025]}, "ict": {y: lv(ict, y) for y in [1998, 2007, 2019, 2025]}, "total": {y: lv(tot, y) for y in [1998, 2007, 2019, 2025]}},
    "yoy_sd_all": {"ep": round(yoy["1105000000"].std(), 1), "total": round(yoy["1000000000"].std(), 1), "ratio": round(yoy["1105000000"].std() / yoy["1000000000"].std(), 2)},
    "lead_corr_ep_t_vs_total_t_plus_L": lead,
    "turning_points": [(str(a), b) for a, b in tp],
    "falls": falls.to_dict("records"), "corr_by_period": corr.to_dict("records"),
    "robust_3ma_corr_total": corr3, "robust_3ma_corr_ict": corr3i, "robust_cut": alt,
}
json.dump(main, open(RES / "main.json", "w"), ensure_ascii=False, indent=1)

# 図1：水準
fig, ax = plt.subplots(figsize=(9, 4.6))
for k, col in [("1105000000", "#d1495b"), ("1000000000", "#333333"), ("1106200000", "#2e86ab")]:
    s = S[k][S[k].index >= start]
    ax.plot(s.index.to_timestamp(), s.values, color=col, lw=1.6 if k != "1000000000" else 1.2, label=NAME[k])
for p, t in pairs:
    ax.axvspan(p.to_timestamp(), t.to_timestamp(), color="#d1495b", alpha=0.08)
ax.set_yscale("log"); ax.yaxis.set_minor_formatter(plt.NullFormatter()); ax.set_yticks([25, 50, 100, 200, 300]); ax.set_yticklabels(["25", "50", "100", "200", "300"])
ax.set_ylabel("生産指数（季節調整済、2020年=100、対数目盛）")
ax.set_title("電子部品は伸びたが、国内の情報通信機械は約3割に（1998年1月〜2026年9月）", fontsize=11)
ax.legend(frameon=False, fontsize=9, loc="lower left"); ax.text(0.99, 0.02, "薄い赤：電子部品の山から谷", transform=ax.transAxes, ha="right", fontsize=8, color="#888")
fig.tight_layout(); fig.savefig(FIG / "a273_levels.png", dpi=150); plt.close()

# 図2：山から谷の下がり幅
fig, ax = plt.subplots(figsize=(8, 4.2))
x = np.arange(len(falls)); w = 0.38
ax.bar(x - w / 2, falls.ep_fall_pct, w, color="#d1495b", label="電子部品・デバイス")
ax.bar(x + w / 2, falls.total_fall_pct_same_months, w, color="#999999", label="鉱工業（同じ月の間）")
for i, r in falls.iterrows():
    ax.text(i - w / 2, r.ep_fall_pct - 1.5, f"{r.ep_fall_pct:.0f}%", ha="center", va="top", fontsize=8)
    ax.text(i + w / 2, min(r.total_fall_pct_same_months, 0) - 1.5, f"{r.total_fall_pct_same_months:.0f}%", ha="center", va="top", fontsize=8)
ax.set_xticks(x); ax.set_xticklabels([f"{r.peak}→\n{r.trough}" for r in falls.itertuples()], fontsize=8)
ax.axhline(0, color="#333", lw=0.8); ax.set_ylabel("山から谷までの変化（%）"); ax.set_ylim(falls.ep_fall_pct.min() - 10, 5)
ax.set_title("電子部品の山から谷までの下がり幅と、同じ月の間の鉱工業", fontsize=11); ax.legend(frameon=False, fontsize=9, loc="lower right")
fig.tight_layout(); fig.savefig(FIG / "a273_falls.png", dpi=150); plt.close()

# 図3：前年同月比の相関（期間別）
fig, ax = plt.subplots(figsize=(7.5, 4))
x = np.arange(len(corr)); w = 0.38
ax.bar(x - w / 2, corr.corr_total, w, color="#333333", label="鉱工業と")
ax.bar(x + w / 2, corr.corr_ict, w, color="#2e86ab", label="情報通信機械と")
for i, r in corr.iterrows():
    ax.text(i - w / 2, r.corr_total + (0.03 if r.corr_total >= 0 else -0.08), f"{r.corr_total:.2f}", ha="center", fontsize=9)
    ax.text(i + w / 2, r.corr_ict + (0.03 if r.corr_ict >= 0 else -0.08), f"{r.corr_ict:.2f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(["1999〜2007年", "2008〜2015年", "2016〜2026年9月"])
ax.axhline(0, color="#333", lw=0.8); ax.set_ylim(-0.4, 1.05); ax.set_ylabel("前年同月比の相関係数")
ax.set_title("電子部品の生産の前年同月比は、2016年以降ほかと一緒に動かなくなった", fontsize=11); ax.legend(frameon=False, fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "a273_corr.png", dpi=150); plt.close()
print(json.dumps({k: main[k] for k in ["level", "yoy_sd_all", "corr_by_period", "robust_3ma_corr_total", "robust_3ma_corr_ict", "robust_cut", "splice_overlap_max_abs_diff"]}, ensure_ascii=False))
print(falls.to_string()); print(lead)
