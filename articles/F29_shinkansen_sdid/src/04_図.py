"""04 図"""
import json
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from common import *
S = json.load(open(RES / "summary.json"))
est = pd.read_csv(RES / "estimates_main.csv")
pct = lambda v: np.expm1(v) * 100

# 図1 石川・富山の実績と合成
fig, axs = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
for ax, tr, f in zip(axs, TREATED, ["series_ishikawa.csv", "series_toyama.csv"]):
    s = pd.read_csv(RES / f, index_col=0, parse_dates=True)
    sm = lambda c: pct(s[c].rolling(3, center=True).mean())
    ax.plot(s.index, sm("actual"), color=ORANGE, lw=2.2, label=f"{tr}（実績）")
    ax.plot(s.index, sm("SCM"), color=BLUE, lw=1.6, label="合成コントロール")
    ax.plot(s.index, sm("SDID"), color=GRAY, lw=1.4, ls="--", label="Synthetic DID")
    ax.axvline(OPEN, color=INK, lw=0.8); ax.text(OPEN, ax.get_ylim()[1] if False else 27, " 2015年3月 開業", fontsize=9, va="top")
    ax.axhline(0, color=GRAY, lw=0.5)
    ax.set_title(f"{tr}県：日本人の延べ宿泊者数"); ax.xaxis.set_major_locator(mdates.YearLocator(1)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.legend(frameon=False, fontsize=9, loc="lower right")
axs[0].set_ylabel("2012/1〜2015/2 の同じ月の平均との差（%、3か月移動平均）")
axs[0].set_ylim(-20, 30)
save(fig, "f01_actual_vs_synth.png")

# 図2 手法別の推定値（石川・富山）
inf = S["inference"]; st = S["structural_ts"]
fig, ax = plt.subplots(figsize=(9, 4.6))
meths = [("DID", "単純な差の差"), ("SCM", "合成コントロール"), ("ASCM", "Augmented SCM"), ("SDID", "Synthetic DID"), ("BSTS", "構造時系列（F04 と同じ流儀）")]
for j, tr in enumerate(TREATED):
    for i, (m, lab) in enumerate(meths):
        yv = i + (0.18 if j == 0 else -0.18)
        if m == "BSTS":
            v = st[tr]["att_pct"]; lo, hi = st[tr]["ci_pct"]
        else:
            v = est[(est.pref == tr) & (est.method == m)].att_pct.iloc[0]
            if m == "SDID": lo, hi = inf[tr]["SDID_ci_pct"]
            else: lo = hi = None
        c = ORANGE if tr == "石川" else BLUE
        ax.plot(v, yv, "o", color=c, ms=8, label=tr if i == 0 else None)
        if lo is not None: ax.plot([lo, hi], [yv, yv], color=c, lw=2)
        ax.text(v, yv + 0.13, f"{v:+.1f}%", fontsize=8.5, ha="center", color=c)
ax.set_yticks(range(len(meths))); ax.set_yticklabels([l for _, l in meths])
ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlabel("2015年3月〜2019年12月の平均の効果（%）　線は95%区間（SDID はプラセボ法、構造時系列はシミュレーション）")
ax.set_title("手法を変えても、石川は＋10〜13%、富山はほぼ0"); ax.legend(frameon=False, loc="lower right")
save(fig, "f02_methods.png")

# 図3 プラセボ（対照県を1つずつ処置とみなした SDID）
pl = pd.read_csv(RES / "placebo_in_space.csv")
pl["SDIDp"] = pct(pl.SDID); pl = pl.sort_values("SDIDp")
fig, ax = plt.subplots(figsize=(9, 7.5))
cols = [ORANGE if p == "石川" else (BLUE if p == "富山" else GRAY) for p in pl.pref]
ax.barh(pl.pref, pl.SDIDp, color=cols)
ax.axvline(0, color=INK, lw=0.6)
ax.set_xlabel("Synthetic DID の推定値（%）。灰色は新幹線の開業がなかった県を「開業した」とみなした値")
r = inf["石川"]["SDID"]
ax.set_title(f"石川は34県中{r['rank']}番目に大きい。プラセボの中にも＋10%を超える県がある")
save(fig, "f03_placebo.png")

# 図4 対照県の重み
w = pd.read_csv(RES / "donor_weights.csv", index_col=0)
w = w.sort_values("石川_SCM", ascending=True)
w = w[(w["石川_SCM"] > 0.005) | (w["石川_SDID"] > 0.04)]
fig, ax = plt.subplots(figsize=(8, 5.5))
yy = np.arange(len(w))
ax.barh(yy + 0.2, w["石川_SCM"], height=0.4, color=BLUE, label="合成コントロール")
ax.barh(yy - 0.2, w["石川_SDID"], height=0.4, color=LIGHT, label="Synthetic DID")
ax.set_yticks(yy); ax.set_yticklabels(w.index)
ax.set_xlabel("「合成石川県」をつくる重み")
ax.set_title("合成コントロールは静岡・山口・愛媛に集中、SDID は広く薄く")
ax.legend(frameon=False, loc="lower right")
save(fig, "f04_weights.png")

# 図5 頑健性と、日本人・外国人
rb = pd.read_csv(RES / "robustness_ishikawa.csv").iloc[::-1]
fig, ax = plt.subplots(figsize=(9.5, 5.6))
yy = np.arange(len(rb))
for m, c, mk in [("SCM", BLUE, "o"), ("SDID", ORANGE, "s"), ("DID", GRAY, "^")]:
    ax.plot(rb[m], yy, mk, color=c, label={"SCM": "合成コントロール", "SDID": "Synthetic DID", "DID": "単純な差の差"}[m], ms=7)
ax.set_yticks(yy); ax.set_yticklabels(rb.variant)
ax.axvline(0, color=GRAY, lw=0.8)
ax.set_xlabel("石川県の効果（%、2015年3月〜2019年12月の平均）")
ax.set_title("対照県・期間を変えても、日本人の宿泊は＋9〜19%")
ax.legend(frameon=False, loc="lower right", fontsize=9)
save(fig, "f05_robustness.png")

# 図6 年ごとの効果と、開業日をずらした時間のプラセボ
yr = pd.read_csv(RES / "effect_by_year_ishikawa.csv"); tp = pd.read_csv(RES / "placebo_in_time.csv")
fig, axs = plt.subplots(1, 2, figsize=(12, 4.2), gridspec_kw=dict(width_ratios=[1.5, 1]))
ax = axs[0]
for m, c in [("SCM", BLUE), ("SDID", ORANGE), ("DID", GRAY)]:
    d = yr[yr.method == m]; ax.plot(d.year, d.pct, "o-", color=c, label={"SCM": "合成コントロール", "SDID": "Synthetic DID", "DID": "単純な差の差"}[m])
ax.set_xticks(sorted(yr.year.unique())); ax.set_ylim(0, 18)
ax.axhline(0, color=GRAY, lw=0.6); ax.set_title("石川：年ごとの効果（2015年は3〜12月）"); ax.set_ylabel("%"); ax.legend(frameon=False, fontsize=9)
ax = axs[1]
lab = [f"{r.pref}\n{r.fake_open.replace('-0', '年')}月" for r in tp.itertuples()]
x = np.arange(len(tp))
ax.bar(x - 0.2, tp.SCM, 0.4, color=BLUE, label="合成コントロール"); ax.bar(x + 0.2, tp.SDID, 0.4, color=ORANGE, label="SDID")
ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8.5); ax.axhline(0, color=GRAY, lw=0.6)
ax.set_ylim(-15, 15); ax.set_title("偽の開業日（2013年3月・2014年3月）では −7〜+4%"); ax.legend(frameon=False, fontsize=8.5)
save(fig, "f06_by_year_and_time_placebo.png")
print("ok")
